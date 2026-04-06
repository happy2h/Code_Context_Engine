from engine.query import QueryEngine

engine = QueryEngine(db_path='/home/fx2h/Projects/Python/context-engine/index_db/context_engine.db')

# 查询符号
symbol = engine.get_symbol('ContextFormatter')
print(symbol)
#
#
# # 全文搜索
# results = engine.search('关键词', limit=10)
#
# # 获取调用者
# callers = engine.get_callers('function_name', depth=1)
#
# # 获取上下文窗口
# ctx = engine.get_context_window('function_name', depth=1)
