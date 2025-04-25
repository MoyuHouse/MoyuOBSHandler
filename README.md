# 摸鱼服务器 OBS 监听

此应用基于 HuaweiCloud OBS 系统与 EG 事件网格进行

## 前提需求

1. 须在 EG 处设置 OBS 配置事件订阅，如下图所示，事件源选择 OBS，类型可选择覆盖的事件，如创建对象注意大文件会分段上传，此时需包括
   OBS:DWR:ObjectCreated:CompleteMultipartUpload 事件
   ![EG 事件配置](./doc_images/hwcloud-eg-subscription.png)
2. 若需要内网访问，则需提前在目标连接中创建对应的网络接口
