"""
Machinery for implementing data handlers that marshal information between widgets and the control system endpoints.
:class:`~comrad.data.channel.CChannel` are received by these handlers and connection is established on corresponding signals and
slots.
"""


# flake8: noqa: E401,E403
from pydm.data_plugins.plugin import PyDMPlugin as CDataPlugin
from ._conn import CDataConnection
from ._common_conn import CCommonDataConnection
from comrad import CChannel, CChannelData
