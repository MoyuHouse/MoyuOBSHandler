# 摸鱼服务器 OBS 监听

此应用基于 HuaweiCloud OBS 系统与 EG 事件网格进行

## 前提需求

1. 须在 EG 处设置 OBS 配置事件订阅，如下图所示，事件源选择 OBS，类型可选择覆盖的事件，如创建对象注意大文件会分段上传，此时需包括
   OBS:DWR:ObjectCreated:CompleteMultipartUpload 事件
   ![EG 事件配置](./doc_images/hwcloud-eg-subscription.png)
2. 若需要内网访问，则需提前在目标连接中创建对应的网络接口
3. 需要提前配置好 obsutil 相关操作，所有的与 OBS 交互的部分都由此工具进行

## 运行说明

需要在 config 目录下创建一个 config.yaml 文件，格式如下：

```yaml
l4d2server:
  obs_bucket: 'OBS 桶名称'
  addons_path: '存放最终 VPK 的目录'
  temp_path: '存放 OBS 下载文件的临时目录'
```
