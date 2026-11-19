这个文件夹用于向C6提供图片源，仅供开发使用，后续会接入相机传输的图片流。

> **测试用临时改动（验证后必须删除）**
>
> 为了演示/联调，固件里临时加入了“每 10 秒重新把本目录内嵌图片塞回上传队列”的周期
> 重发逻辑，**仅用于测试，不用于正式部署**。
>
> ### 改了什么
>
> 1. `firmware/main/Kconfig.projbuild` 新增选项：
>
>    ```kconfig
>    config APP_IMAGE_SELFTEST_PERIOD_S
>        int "Re-seed embedded self-test images every N seconds"
>        default 0
>        range 0 3600
>    ```
>
> 2. `firmware/components/mqtt_serial/mqtt_serial.c` 的 `mqtt_task()`：
>    - 首次 MQTT 就绪时 `image_upload_prime()`（原有行为）；
>    - 当 `CONFIG_APP_IMAGE_SELFTEST_PERIOD_S > 0` 时，每隔 N 秒再次调用
>      `image_upload_prime()`，把内嵌图重新入队。
>
> 3. 板级配置（构建目录，不入库）：
>    `build/mqtt_serial/nodes/ugv-001/ugv-chain/sdkconfig` 中
>    `CONFIG_APP_IMAGE_SELFTEST_PERIOD_S=10`。
>
> ### 为什么
>
> 没有真实视频帧源时，让 L2 叶子持续产生上传流量，便于观察
> `C6 → WiFi mesh → root C6 → USB 隧道 → Jetson 落盘` 整条链路与清理策略。
>
> ### 如何彻底删除
>
> 1. 板级 `sdkconfig` 改回 `CONFIG_APP_IMAGE_SELFTEST_PERIOD_S=0`（或删掉该行，默认即 0），
>    重新编译烧录；
> 2. 删除 `mqtt_serial.c` 中 `#if CONFIG_APP_IMAGE_SELFTEST_PERIOD_S > 0` 包裹的周期重发
>    代码与 `last_prime` 变量；
> 3. 删除 `firmware/main/Kconfig.projbuild` 中对应的 Kconfig 选项；
> 4. 删除本节说明。
