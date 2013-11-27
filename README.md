### Deprecated
see [flask-restful-extend](https://github.com/anjianshi/flask-restful-extend)



```text

# 核心

APIManager (API 装饰器；可扩展)
    通过调用此对象来包装并注册 API handler

返回值 json 化（可扩展）
    API handler 的返回值一律转换为 json 字符串返回给客户端
    用户可自行扩展，以处理默认 json 解析器无法处理的值

处理异常
    flask-json-api 不进行异常处理，因为这个工作通常是在针对 app 全局进行的，而 api 往往只是全局的一部分。
    不过作为建议，API handler 中若要抛出异常，应使用 HTTPException 及其子类
    对于不可预见的异常，在 debug 状态下，会直接将其抛出，并输出错误细节。在生产状态下，会转换成 500 错误，没有信息被输出和记录。
    可以手动给 app 指定一个 log_handler 将它记录下来

API handler 互相调用
    这个不用过多处理，只要保证装饰器装饰 api 函数后，返回的是原函数就行。
    关于解决输入的问题，api 函数从两个地方获取输入：
        1. url 参数，这个是通过函数参数传给它的。这些参数有可能被 URL variable 转换器转换过，这种转换过的参数一般是把 id 转换成数据库对象。
           一个 api 函数调用其他 api 函数时，就根据其要求把参数传过去就行。
           [对于 conv 过的，可预先把这些对象创建好再传给它。] 不行！目前有问题。只能通过参数名称传递参数。无法跳过 conv
           （在很多情况下，当前 api 函数本身就需要这些对象，因此早已经构造好了）
        2. request.json, request.form
           需要从这里面提取输入的 api 函数，建议只通过 url 调用。
           如果需要，以后可能提供一个接口，把参数封装成 json/form ，通过本地 http 请求，
           来调用对应的 api 函数，然后把函数的 json 返回值解析回 python 值，以实现完整、彻底的 api 函数调用另一个 api 函数的功能



---------------------------------------------------------


# conv

URL variable 转换器(可扩展)
    这个转换器不同于 Flask 里的 converter，是以装饰器的形式实现的。
    它可以接收参数，同时允许你改变 variable 的名称（例如：在 URL 中以 cat_id 命名，但转换后以 cat 为参数名传给 API handler）
    用户可基于基类，生成自己的转换器



---------------------------------------------------------


# auth

权限验证(可扩展)
    系统提供一系列接口，包括：
        向客户端写入身份信息（登录）
        获取身份信息
        清除客户端的身份信息（退出）
        权限检查（看用户当前的身份信息是否符合 API handler 的要求）



---------------------------------------------------------


# form （针对 wtforms ）

优化了 wtforms 的默认表单类：
    解决 wtforms 不支持 json form(request.json) 的问题
    让表单在验证失败时自动报错

优化了 wtforms-alchemy 的 model_form，详见源代码



---------------------------------------------------------


# db （针对 sqlalchemy）

通过添加 as_dict() 方法，解决 SQLAlchemy 对象无法 json 化的问题
给 SQLAlchemy 的 Model 对象增加了一个 __api_args__ 的属性，用来存放此模块用到的一些配置

创建一个专门针对 model 的 url variable converter

提供一个简易的 validator 工具
class User(db.Model)
    name = Column(String(100), nullable=False)
    v1 = validator('name', 'min_length', 3)

```
