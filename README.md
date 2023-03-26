# 简单区块链的python实现

利用flask实现简单区块链，定义了数据结构区块Block，区块链Blockchain，模拟实现了交易数据添加到区块链中以及区块链数据在节点间的广播

## 启动方式

后端节点代码在[node_server.py](./node_server.py)文件中，前端使用了Vue和element-plus，代码文件在[index.html](./index.html)中

可将node_server.py文件复制三份，分别运行在5000，5001，5002端口

浏览器打开index.html，可看到以下界面：

![image.png](https://s2.loli.net/2023/03/26/iL8G1UN3dylXDFn.png)

首先选择启动节点，再将其它节点注册到该节点，

每个节点都可独立添加交易信息，点击挖矿进行获得工作量证明后可将交易信息添加到区块中