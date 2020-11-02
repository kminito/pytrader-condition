import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import pandas as pd
import sqlite3

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.condition = {}

    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)

        ## 조건검색식 관련 추가
        self.OnReceiveConditionVer.connect(self.receiveConditionVer)
        self.OnReceiveTrCondition.connect(self.receiveTrCondition)
        self.OnReceiveRealCondition.connect(self.receiveRealCondition)


    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _event_connect(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("disconnected")

        self.login_event_loop.exit()

    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]

    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    def get_connect_state(self):
        ret = self.dynamicCall("GetConnectState()")
        return ret

    def get_login_info(self, tag):
        ret = self.dynamicCall("GetLoginInfo(QString)", tag)
        return ret

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                         [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no])

    def get_chejan_data(self, fid):
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        print(gubun)
        print(self.get_chejan_data(9203))
        print(self.get_chejan_data(302))
        print(self.get_chejan_data(900))
        print(self.get_chejan_data(901))

    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if next == '2':
            self.remained_data = True
        else:
            self.remained_data = False

        if rqname == "opt10081_req":
            self._opt10081(rqname, trcode)

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)

        for i in range(data_cnt):
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.ohlcv['date'].append(date)
            self.ohlcv['open'].append(int(open))
            self.ohlcv['high'].append(int(high))
            self.ohlcv['low'].append(int(low))
            self.ohlcv['close'].append(int(close))
            self.ohlcv['volume'].append(int(volume))


    ###############################################################
    # 메서드 정의: 조건검색 관련 메서드와 이벤트                    #
    ###############################################################

    def receiveConditionVer(self, receive, msg):
        """
        getConditionLoad() 메서드의 조건식 목록 요청에 대한 응답 이벤트

        :param receive: int - 응답결과(1: 성공, 나머지 실패)
        :param msg: string - 메세지
        """
        print("[receiveConditionVer]")
        try:
            if not receive:
                return
                
            self.condition = self.getConditionNameList()
            print("조건식 개수: ", len(self.condition))

            for key in self.condition.keys():
                print("조건식: ", key, ": ", self.condition[key])
                # print("key type: ", type(key))

        except Exception as e:
            print(e)

        finally:
            self.conditionLoop.exit()


    def receiveTrCondition(self, screenNo, codes, conditionName, conditionIndex, inquiry):
        """
        (1회성, 실시간) 종목 조건검색 요청시 발생되는 이벤트

        :param screenNo: string
        :param codes: string - 종목코드 목록(각 종목은 세미콜론으로 구분됨)
        :param conditionName: string - 조건식 이름
        :param conditionIndex: int - 조건식 인덱스
        :param inquiry: int - 조회구분(0: 남은데이터 없음, 2: 남은데이터 있음)
        """

        print("[receiveTrCondition]")
        try:
            if codes == "":
                return

            codeList = codes.split(';')
            del codeList[-1]

            print(codeList)
            print("종목개수: ", len(codeList))
           
        finally:
            self.conditionLoop.exit()


    def receiveRealCondition(self, code, event, conditionName, conditionIndex):
        print("[receiveRealCondition]")
        """
        실시간 종목 조건검색 요청시 발생되는 이벤트

        :param code: string - 종목코드
        :param event: string - 이벤트종류("I": 종목편입, "D": 종목이탈)
        :param conditionName: string - 조건식 이름
        :param conditionIndex: string - 조건식 인덱스(여기서만 인덱스가 string 타입으로 전달됨)
        """

        print("종목코드: {}, 종목명: {}".format(code, self.get_master_code_name(code)))
        
        print("이벤트: ", "종목편입" if event == "I" else "종목이탈")
        
        # bot.sendMessage(chat_id=chat_id, text="종목코드: {} , {}".format(code, event))

    def getConditionLoad(self):
        print("[getConditionLoad]")
        """ 조건식 목록 요청 메서드 """

        isLoad = self.dynamicCall("GetConditionLoad()")
        # 요청 실패시
        if not isLoad:
            print("getConditionLoad(): 조건식 요청 실패")

        # receiveConditionVer() 이벤트 메서드에서 루프 종료
        self.conditionLoop = QEventLoop()
        self.conditionLoop.exec_()

    def getConditionNameList(self):
        print("[getConditionNameList]")
        """
        조건식 획득 메서드

        조건식을 딕셔너리 형태로 반환합니다.
        이 메서드는 반드시 receiveConditionVer() 이벤트 메서드안에서 사용해야 합니다.

        :return: dict - {인덱스:조건명, 인덱스:조건명, ...}
        """

        data = self.dynamicCall("GetConditionNameList()")

        if data == "":
            print("getConditionNameList(): 사용자 조건식이 없습니다.")

        conditionList = data.split(';')
        del conditionList[-1]

        conditionDictionary = {}

        for condition in conditionList:
            key, value = condition.split('^')
            conditionDictionary[int(key)] = value

        return conditionDictionary

    def sendCondition(self, screenNo, conditionName, conditionIndex, isRealTime):
        print("[sendCondition]")
        """
        종목 조건검색 요청 메서드

        이 메서드로 얻고자 하는 것은 해당 조건에 맞는 종목코드이다.
        해당 종목에 대한 상세정보는 setRealReg() 메서드로 요청할 수 있다.
        요청이 실패하는 경우는, 해당 조건식이 없거나, 조건명과 인덱스가 맞지 않거나, 조회 횟수를 초과하는 경우 발생한다.

        조건검색에 대한 결과는
        1회성 조회의 경우, receiveTrCondition() 이벤트로 결과값이 전달되며
        실시간 조회의 경우, receiveTrCondition()과 receiveRealCondition() 이벤트로 결과값이 전달된다.

        :param screenNo: string
        :param conditionName: string - 조건식 이름
        :param conditionIndex: int - 조건식 인덱스
        :param isRealTime: int - 조건검색 조회구분(0: 1회성 조회, 1: 실시간 조회)
        """


        isRequest = self.dynamicCall("SendCondition(QString, QString, int, int",
                                     screenNo, conditionName, conditionIndex, isRealTime)

        if not isRequest:
            print("sendCondition(): 조건검색 요청 실패")

        # receiveTrCondition() 이벤트 메서드에서 루프 종료
        self.conditionLoop = QEventLoop()
        self.conditionLoop.exec_()

    def sendConditionStop(self, screenNo, conditionName, conditionIndex):

        print("[sendConditionStop]")
        """ 종목 조건검색 중지 메서드 """

        self.dynamicCall("SendConditionStop(QString, QString, int)", screenNo, conditionName, conditionIndex)







if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    kiwoom.getConditionLoad()
    """
    :param screenNo: string
    :param conditionName: string - 조건식 이름
    :param conditionIndex: int - 조건식 인덱스
    :param isRealTime: int - 조건검색 조회구분(0: 1회성 조회, 1: 실시간 조회)
    """        
    kiwoom.sendCondition("0","단타2",2,1)