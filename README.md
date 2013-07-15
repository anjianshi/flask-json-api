```text

kgzx-api

api 装饰器
    将错误处理、权限验证、返回值格式化组件与 api 函数拼装在一起，并注册进 app.route


错误处理(控制返回的 http status 和 body，可自行扩展)
    让每种可预期的异常都有对应的返回给客户端的 http status 和 body(字符串，非 json 格式)
    用户可自行注册异常与对应的返回值

格式化返回值（可自行扩展）
    api 函数的返回值一律转换为 json 字符串格式，返回给客户端
    用户如果有特殊的、默认 json 解析器无法处理的返回值，可自行扩展，添加处理逻辑

权限验证(独立于 api 系统，可自行扩展)
    系统提供一系列接口，包括：
        向客户端写入身份信息（登录）
        获取身份信息
        清除客户端的身份信息（退出）
        权限检查（看用户当前的身份信息是否符合 api 函数的要求）
    身份类型时由用户定义的，每种身份类型需对应一个数字。
    指定 api 函数的权限需求时，把允许的多个身份类型的值进行按位运算，传给 api 装饰器

    例子：
    Auth.ADMIN = 1
    Auth.CUSTOMER = 2
    Auth.ANONYMOUS = 4

    auth = SessionAuthManager(app)

    @api('/index')
    @auth(Auth.ANONYMOUS)
    def index():
        pass

    @api('/list', auth=Auth.ADMIN)
    @auth(Auth.CUSTOMER)
    def li():
        pass

api 函数 参数转换(独立于 api 系统，可自行扩展)
    参数转换系统根据用户给出的规则，转换、校验某个 url 参数的值，例如把分类 id 转换为分类对象
    用户可基于基类，生成自己的转换器

api 函数互相调用
    这个不用过多处理，只要保证装饰器装饰 api 函数后，返回的是原函数就行。
    关于解决输入的问题，api 函数从两个地方获取输入：
        1. url 参数，这个是通过函数参数传给它的。这些参数有可能被 route converter 转换过，这种转换过的参数一般是把 id 转换成数据库对象。
           一个 api 函数调用其他 api 函数时，就根据其要求把参数传过去就行。对于 conv 过的，可预先把这些对象创建好再传给它。
           （在很多情况下，当前 api 函数本身就需要这些对象，因此早已经构造好了）
        2. request.json, request.form
           需要从这里面提取输入的 api 函数，建议只通过 url 调用。
           如果需要，以后可能提供一个接口，把参数封装成 json/form ，通过本地 http 请求，
           来调用对应的 api 函数，然后把函数的 json 返回值解析回 python 值，以实现完整、彻底的 api 函数调用另一个 api 函数的功能



---------------------------------------------------------

form fix （针对 wtforms ）

解决 wtforms 不支持 json form(request.json) 的问题
让表单在验证失败时自动报错



---------------------------------------------------------


database fix （针对 sqlalchemy）

解决数据库对象(model, query, KeyedTuple)无法转换为 json 的问题

```