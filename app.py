from PyQt5.QtCore import QSharedMemory
from loguru import logger
import os
import sys
import conf

share = QSharedMemory('ClassWidgets')

def createShared():
    global share
    share.create(1)  # 创建共享内存
    logger.info(f"共享内存：{share.isAttached()} 是否允许多开实例：{conf.read_conf('Other', 'multiple_programs')}")


def restart():
    global share
    logger.debug('重启程序')
    share.detach()
    os.execl(sys.executable, sys.executable, *sys.argv)