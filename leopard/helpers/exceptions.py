class TenderCheckException(Exception):
    """投标异常"""

    def __init__(self, message):
        super(TenderCheckException, self).__init__(message)
        self.message = message


class RepaymethodDoesNotexist(Exception):
    """不存在的还款方式"""

    def __init__(self, message):
        super(RepaymethodDoesNotexist, self).__init__(message)
        self.message = message


class FlowOperationException(Exception):
    """流标操作异常"""

    def __init__(self, message):
        super(FlowOperationException, self).__init__(message)
        self.message = message
