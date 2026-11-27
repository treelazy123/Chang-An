# 企业技术标准（评审草案）

# MCI 方法描述与发现接口规范

MCI Method Description and Discovery Interface Specification

| 文档控制项 | 内容 |
| --- | --- |
| 标准编号 | 待企业标准管理部门分配 |
| 文档版本 | 1.0.0 |
| 文档状态 | 评审草案 |
| 修订日期 | 2026-11-19 |
| 发布单位 | 待确定 |
| 归口部门 | 待确定 |
| 起草部门 | 待确定 |
| 批准人 | 待审批 |
| 发布日期 | 批准后确定 |
| 实施日期 | 批准后确定 |

## 前言

本文件用于统一 MCI 方法命名、方法描述及发现接口的数据约定，为服务提供方、注册中心和调用方的开发、联调及验收提供依据。

本文件正文为规范性内容；附录 A 为资料性内容。标准编号、发布单位、归口部门及实施日期由企业完成评审批准后确定。

本次修订保留业务字段逐项说明，并将 `listMethod` 的成功返回清单调整为“服务清单 → 方法清单 → 输入/输出契约”的层级结构，同一服务名称不再随每个方法重复返回。

## 目录

1. 范围
2. 规范性引用文件
3. 术语、定义和缩略语
4. 总体要求
5. 服务与方法命名
6. 服务及方法描述数据模型
7. 方法发现接口
8. 校验与发布要求
9. 版本与兼容性
10. 符合性检查

附录 A（资料性） listMethod 返回示例与字段说明

## 1 范围

本文件规定了 MCI 服务及方法的命名规则、服务及方法描述数据模型、`listMethod` 方法发现接口、校验发布要求和版本兼容性要求。

本文件适用于服务提供方、注册中心及调用方之间的方法描述发布、目录维护、方法发现和接口一致性验收。

本文件定义应用层数据结构，不指定 HTTP、WebSocket、消息总线或其他传输方式，不规定鉴权机制、调用报文外壳及异步控制任务的完整生命周期。采用具体传输协议时，应另行规定协议绑定方式。

## 2 规范性引用文件

下列文件的内容通过文中的规范性引用构成本文件必不可少的条款。注日期或注明版本的引用文件，仅该日期或版本对应的内容适用于本文件。

- JSON Schema Draft 2020-12，JSON Schema Core。
- JSON Schema Draft 2020-12，JSON Schema Validation。

上述文件用于确定 Schema 的结构、关键字及校验语义；本文件增加的数据结构和业务约束应同时满足。

## 3 术语、定义和缩略语

### 3.1 服务（service）

对一组相关业务方法的稳定逻辑归类；服务身份不同于某个运行实例的地址或设备编号。

### 3.2 方法（method）

服务中具有明确业务语义和输入、输出约定的操作或消息类型，由所属服务名和方法名共同标识。

### 3.3 服务描述对象（Service Descriptor）

包含服务名及其方法描述数组的数据对象，用于将同一服务的方法集中组织。

### 3.4 方法描述对象（Method Descriptor）

包含方法名、方法说明、输入 Schema 和输出 Schema 的数据对象，其服务归属由父级服务描述对象确定。

### 3.5 数据契约（Schema）

采用 JSON Schema 表达的数据类型、字段、必填性和取值约束，不是实际业务参数或结果。

### 3.6 方法发现（Method Discovery）

调用方根据筛选条件获取当前可见服务及其方法完整描述的过程。

### 3.7 缩略语

| 缩略语 | 说明 |
| --- | --- |
| MCI | 本系统接口名称标识，本文不扩展其英文全称 |
| JSON | JavaScript Object Notation，JavaScript 对象表示法 |
| ASCII | American Standard Code for Information Interchange，美国信息交换标准代码 |

## 4 总体要求

### 4.1 条款用语

“应”“不应”分别表示要求和禁止；“宜”“不宜”分别表示推荐和不推荐；“可”表示允许。本文件不另设与上述用语并行的要求等级。

### 4.2 参与方职责

| 参与方 | 职责 |
| --- | --- |
| 服务提供方 | 编制并发布有效描述，保持实例间定义一致，校验调用输入并保证输出符合契约 |
| 注册中心 | 校验并维护描述目录，提供一致的发现快照，合并同一服务及同一方法的实例描述 |
| 调用方 | 按服务和方法层级解析清单，识别协议版本，依据已发布契约构造请求及处理结果 |

### 4.3 数据组织原则

发现清单应采用 `services[].methods[]` 结构。服务名应在服务描述对象中声明一次，其下全部方法共用该服务名；方法对象中不应重复设置 `service`。

输入及输出契约应描述业务数据，不应混入路由、鉴权等传输协议公共字段。发现权限与业务调用权限应分别控制。

## 5 服务与方法命名

### 5.1 service

`service` 表示方法所属的稳定业务服务，不携带方法语义前缀。

服务名采用下划线分段结构：

```text
<业务域标识>_<服务标识>[_<子服务标识>...]
```

例如 `Loco_Robot`，业务域和服务标识的具体含义由业务命名表统一定义。

| 项目      | 要求                                                   |
| ------- | ---------------------------------------------------- |
| 类型      | string                                               |
| 长度      | 3～64 个 ASCII 字符，包含下划线                                |
| 允许字符    | 英文字母、数字、下划线                                          |
| 分段规则    | 至少两段，以单个下划线分隔；每段以大写英文字母开头，后续为字母或数字                   |
| 命名风格    | 每段宜使用 PascalCase，已有业务缩写可保留，如 `Loco_Robot`           |
| 结构正则表达式 | `^[A-Z][A-Za-z0-9]*(?:_[A-Z][A-Za-z0-9]*)+$`；总长度另行校验 |
| 大小写     | 区分大小写                                                |

服务名不应包含空格、中文、点号或连字符，不应出现首尾下划线、连续下划线或空分段。不应用实例编号、设备序列号替代服务名。实例身份由传输层或注册信息表达。

合法示例：`Loco_Robot`、`Base_File`、`Base_Log`、`Loco_Robot_Navigation`。非法示例：`LocoRobot`、`loco_Robot`、`Loco_robot`、`Loco__Robot`、`Loco_Robot_`、`Loco.Robot`。

### 5.2 method

方法名结构：

```text
<语义前缀>_<业务标识>[_<业务标识>...]
```

| 项目    | 要求                                 |
| ----- | ---------------------------------- |
| 类型    | string                             |
| 总长度   | 1～128 个 ASCII 字符，包含前缀及下划线          |
| 允许前缀  | `Cnr`、`Get`、`Ntf`、`Et`、`Dat`，大小写固定 |
| 业务标识  | 每段以大写字母开头，后续为字母或数字                 |
| 正则表达式 | `^(Cnr\|Get\|Ntf\|Et\|Dat)_[A-Z][A-Za-z0-9]*(?:_[A-Z][A-Za-z0-9]*)*$` |
| 大小写   | 区分大小写                              |

业务名称宜使用 PascalCase；已有业务编码、缩写可保留，如 `RR`、`RS001`。不应出现连续下划线、尾部下划线、空业务标识或其他未定义前缀。

### 5.3 前缀语义

| 前缀     | 语义                    | 示例                                | 本版本消息模式 |
| ------ | --------------------- | --------------------------------- | ------- |
| `Cnr_` | 控制请求，以及该请求的接收确认或执行结果  | `Cnr_RR_Navigate`                 | 请求—响应   |
| `Get_` | 查询配置、状态或资源，不应产生业务状态变更 | `Get_LogConfig`、`Get_SearchFiles` | 请求—响应   |
| `Ntf_` | 状态变化、处理进度等通知          | `Ntf_LogConfigChanged`            | 单向消息    |
| `Et_`  | 已发生业务事件的上报            | `Et_RS001`                        | 单向消息    |
| `Dat_` | 业务数据、采样数据或数据批次传输      | `Dat_Telemetry`                   | 单向消息    |

`Cnr_` 返回的是“已收到”“已受理”还是“执行完成”，应在方法 `description` 及 `outputSchema` 字段说明中明确，不应把受理成功描述为执行成功。业务协议如同时支持受理和最终结果，应另行明确状态、任务标识和结果关联规则。

`RR`、`RS001` 等业务标识的含义由业务协议定义，不应仅凭名称推断其表示接收确认、执行结果或某种事件。

`Ntf_`、`Et_`、`Dat_` 的前缀表示消息语义，不固定网络方向：发布者可为任意业务参与方。消息发现不等于调用授权，发现的单向消息不应自动作为普通请求—响应方法调用。需要业务确认的数据提交，应使用 `Cnr_` 并定义响应。

### 5.4 唯一标识

在同一服务目录范围内，`(service, method)` 应唯一。多个实例提供相同方法时应合并发现项；不同实例不应对同一标识发布冲突定义。

文档或日志可使用 `service.method` 表示方法全名，例如 `Loco_Robot.Cnr_RR_Navigate`。发现返回中，`service` 由服务描述对象提供，`method` 由其下的方法描述对象提供；二者通过父子层级关联。不应将方法全名写入 `method`。

### 5.5 业务参数名称

输入、输出及单向消息载荷中，所有 `properties` 对象下的业务字段名应遵循本节规定，包括嵌套对象、数组元素对象和 `$defs` 中对象定义的字段名。这里的名称是实际业务数据的 key，不是 JSON Schema 关键字。

| 项目 | 要求 |
| --- | --- |
| 类型及长度 | string，1～64 个 ASCII 字符 |
| 允许字符 | 英文字母、数字；首字符应为小写英文字母 |
| 命名风格 | 小驼峰（lowerCamelCase）：首个单词小写，后续单词首字母大写，例如 `maxResults`、`targetId` |
| 结构正则表达式 | `^[a-z][A-Za-z0-9]*$`；总长度及单词大小写风格另行校验 |
| 缩略语 | 宜作为普通单词处理，例如 `taskId`、`httpUrl`，不宜写为 `taskID`、`HTTPUrl` |
| 语义 | 应使用明确的业务名称；同一业务含义在相关输入、输出和事件中宜使用相同名称 |
| 大小写与唯一性 | 区分大小写；同一对象中不应存在重复 key，也不宜仅通过大小写差异区分字段 |

业务字段名不应包含中文、空格、下划线、连字符、点号或其他特殊字符，不应以数字或大写字母开头。`required` 中的名称应与同层 `properties` 中的字段名完全一致，不应自动转换大小写或命名风格。

合法示例：`query`、`maxResults`、`targetId`、`taskId`、`results`、`path`、`joint1Angle`。非法示例：`MaxResults`、`max_results`、`target-id`、`1stTarget`、`目标点`。

本节不改变 `inputSchema`、`outputSchema` 等协议固定字段名，也不适用于 `$ref`、`$defs` 等 Schema 关键字或 `enum` 的业务取值。`$defs` 内的定义名不是业务参数名，可使用 `Entry` 等类型名称。

## 6 服务及方法描述数据模型

### 6.1 字段层级与定义

服务描述对象（Service Descriptor）用于组织同一服务的方法。每个方法描述对象（Method Descriptor）从直接父级服务描述对象继承所属服务，不重复设置 `service`。

```text
服务描述对象 / Service Descriptor
├── service                         服务名，同一服务仅出现一次
└── methods                         该服务下的方法描述数组
    └── []                          一个方法描述对象
        ├── method                  方法名
        ├── description             方法用途、行为和限制
        ├── inputSchema             输入数据契约
        │   ├── type                根输入数据类型，固定为 object
        │   ├── properties          输入业务字段定义表
        │   │   └── <业务字段名>     某个输入字段的 Schema
        │   │       ├── type 或 $ref 字段类型或本地引用
        │   │       ├── description  字段业务含义
        │   │       └── <约束关键字> 范围、长度、枚举等约束
        │   ├── required            输入必填字段名列表，可省略
        │   └── additionalProperties 是否允许未声明的输入字段
        └── outputSchema            输出数据契约；单向消息为 null
            ├── type                根输出数据类型，固定为 object
            ├── properties          输出业务字段定义表，可继续嵌套
            ├── required            输出必填字段名列表，可省略
            └── additionalProperties 是否允许未声明的输出字段
```

层级图仅展示结构，不是 JSON 报文；`[]` 表示数组元素，`<业务字段名>`、`<约束关键字>` 为占位说明。可选的 `$defs` 及嵌套对象、数组的关键字说明见 6.4 节。

表 1 — 服务描述对象字段

| 字段（key） | 类型 | 必填 | 含义与约束 |
| --- | --- | --- | --- |
| `service` | string | 是 | 稳定业务服务名，符合 5.1 节；为当前 `methods` 中所有方法提供服务归属 |
| `methods` | array of object | 是 | 当前服务中满足筛选条件且对调用方可见的方法描述对象数组；至少包含一个元素 |

服务描述对象仅允许上述两个字段。同一次发现返回中，每个服务名只能出现一次；同一服务的所有匹配方法应合并到该对象的 `methods` 数组中。

表 2 — 方法描述对象字段

| 字段（key） | 类型 | 必填 | 含义与约束 |
| --- | --- | --- | --- |
| `method` | string | 是 | 当前服务中的具体业务方法名；前缀表达消息语义，符合 5.2、5.3 节；与父级 `service` 共同确定方法身份 |
| `description` | string | 是 | 按“用户描述&详细描述”组织的方法说明，格式见 6.5 节；总长度为 1～2048 个 Unicode 码点，包含分隔符 |
| `inputSchema` | object | 是 | 定义请求参数对象或单向消息载荷的字段、类型和约束；存放 Schema，不是实际输入值 |
| `outputSchema` | object 或 null | 是 | 定义成功响应业务结果的字段、类型和约束；存放 Schema，不是实际结果。单向消息固定为 JSON 字面值 `null` |

方法描述对象仅允许上述四个字段，不应重复设置 `service`，也不应额外添加 `name`、`type` 等未定义字段。方法描述不应脱离服务上下文发布；单独传递某个方法描述时，应以包含该方法的服务描述对象承载。扩展字段须通过后续规范版本定义。

`description` 应说明业务用途、关键行为和限制。控制方法还应明确响应阶段；事件编码方法应说明编码的业务含义。不应仅重复方法名或使用“接口”“方法”等无实际信息的描述。

### 6.2 Schema 方言及基础规则

本规范统一采用 JSON Schema Draft 2020-12。所有 `inputSchema` 和非 null 的 `outputSchema` 应按该版本解析；实现方应显式配置对应方言的校验器，不应依赖校验库的默认版本。每个非 null 的根 Schema 应声明对象类型。以下为空对象的完整 Schema 示例：

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

这是本规范选用的 Schema 方言，相关关键字按 [JSON Schema Draft 2020-12 官方规范](https://json-schema.org/draft/2020-12/json-schema-core)解释。

强制要求：

1. `inputSchema` 及非 null 的 `outputSchema` 应是合法的 Schema 对象；本版本不接受布尔形式的根 Schema。
2. 根数据类型应为 `object`，根层应提供 `properties` 和布尔类型的 `additionalProperties`。
3. 本版本采用显式对象定义：每个用于描述数据对象的子 Schema，也应提供 `properties` 和布尔类型的 `additionalProperties`。宜默认选择 `false`；确需开放扩展时可选择 `true`，并在描述中说明用途。
4. 必填字段应列入 `required`；`required` 中的名称应在同一对象的 `properties` 中定义。没有必填字段时，可省略 `required`。
5. 数组应定义 `items`；固定候选值宜使用 `enum` 或 `const`；数值、字符串和数组宜按业务需要设置取值范围或长度限制。
6. `properties` 中每个业务字段应有符合 5.5 节的名称及符合 6.5 节的 `description`，并明确类型或通过引用给出其约束。
7. `$ref` 仅允许当前根 Schema 内的 JSON Pointer 引用，例如 `#/$defs/Entry`；不应依赖外部网络或另一个根 Schema。本版本不使用 `$id`、`$anchor`、`$dynamicRef` 和 `$dynamicAnchor`。
8. 缺失、`null` 与空对象具有不同含义，禁止相互替代。字段允许 null 时，应在对应 Schema 中显式声明。
9. Schema 中的 `default` 仅用于说明建议默认值；如存在运行时补默认值的行为，应在字段说明中明确约定，由业务实现执行。

`properties` 本身不会要求字段出现，`additionalProperties` 默认也不会禁止额外字段；因此需要显式声明必填性和扩展策略。参见 [JSON Schema 对象官方说明](https://json-schema.org/understanding-json-schema/reference/object)。

### 6.3 输入与输出语义

| 方法类别                | `inputSchema` 校验的数据 | `outputSchema` 校验的数据 |
| ------------------- | ------------------- | -------------------- |
| `Cnr_`、`Get_`       | 请求中的业务参数对象          | 成功响应中的业务结果对象         |
| `Ntf_`、`Et_`、`Dat_` | 发布的消息载荷对象           | 无业务响应，应为 `null`     |

Schema 只描述业务参数或业务结果，不包含传输协议公共外壳，如请求 ID、路由头和统一错误对象。单向消息可有底层传输确认，但这种确认不属于业务 `outputSchema`。

无参数方法的 `inputSchema` 应使用以下形式，实际传入值为 `{}`：

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

需要成功响应但无业务结果的请求—响应方法，`outputSchema` 也使用上述空对象 Schema，实际结果为 `{}`。

注意：描述对象中的 `"outputSchema": null` 表示没有业务响应；`"outputSchema": {"type": "null"}` 表示存在值为 null 的响应，后者不属于本版本支持的根输出类型。

### 6.4 Schema 内部 key 说明

#### 6.4.1 路径与层级约定

以下使用 `S` 代表 `inputSchema`、非 null 的 `outputSchema`，或其中的一个子 Schema；路径中的 `[]` 表示数组元素，`<字段名>` 表示业务自行定义的 key。路径用于文档定位，不是需要发送的字段。

例如 `inputSchema.properties.query.description` 表示“输入参数 `query` 的说明”；`outputSchema.properties.results.items.properties.path.description` 表示“结果数组中每个元素的 `path` 字段说明”。实际业务数据中的对应路径分别为 `query` 和 `results[].path`，不携带 `properties`、`items` 等 Schema 关键字。

#### 6.4.2 类型、对象与数组结构

| key / 所在层级                         | 值类型                      | 出现要求                     | 说明                                                                                                                                 |
| ---------------------------------- | ------------------------ | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `S.type`                           | string 或 array of string | 根层应；业务字段可通过 `$ref` 给出约束 | 声明被校验数据的类型。根层固定为 `"object"`；业务字段可使用 `string`、`integer`、`number`、`boolean`、`object`、`array`、`null` 等类型；允许空值可写成 `["string", "null"]` |
| `S.description` | string | `properties` 中每个业务字段应提供 | 按 6.5 节以 `&` 分隔用户描述与详细描述，说明当前字段的业务含义、单位、取值解释、缺省行为或限制，不替代方法顶层的 `description` |
| 对象 Schema 的 `properties`           | object                   | 每个数据对象 Schema 应提供       | 字段定义表；其中每个 key 是实际业务字段名，每个 value 是该字段的 Schema。空对象使用 `{}`                                                                           |
| `S.properties.<字段名>`               | object 或其他合法子 Schema 形式  | 声明业务字段时提供                | 描述单个业务字段。本规范要求业务字段具有非空 `description`，并明确类型或通过引用给出约束；示例采用对象形式承载这些信息                                                                 |
| 对象 Schema 的 `required`             | array of string          | 有必填字段时应提供               | 列出当前对象中应出现的业务字段名，且名称应在同层 `properties` 中定义。父对象必填与子字段必填分别声明                                                                        |
| 对象 Schema 的 `additionalProperties` | boolean                  | 每个数据对象 Schema 应提供       | `false` 禁止当前对象包含未在 `properties` 中声明的字段；`true` 允许扩展字段并须说明用途。该设置不自动传递到嵌套对象                                                           |
| 数组 Schema 的 `items`                | Schema；本文示例为 object      | 每个数组应提供                 | 定义数组元素的共同约束。元素为对象时，在 `items` 内继续定义 `type`、`properties`、`required` 和 `additionalProperties`                                         |
| 根 Schema 的 `$defs`                 | object                   | 使用可复用定义时提供               | 存放当前根 Schema 内的命名子 Schema；定义名不是实际业务数据字段，声明定义本身不会让数据自动使用它                                                                           |
| `S.$ref`                           | string                   | 使用引用时提供                  | 引用当前根 Schema 中的定义或其他位置，如 `#/$defs/Entry`。输入、输出是不同根 Schema，不能跨根引用；引用字段仍须按 6.2 节提供非空 `description`                                   |

`required` 约束字段是否出现，`type` 约束字段出现后的值类型，两者独立。例如字段列入 `required` 且类型允许 `null`，表示应提供该 key，但其值可为 `null`。嵌套对象的子字段列入其内部 `required`，并不意味着父对象字段自动必填。

#### 6.4.3 取值与长度约束

下表说明本文涉及的常用约束关键字；是否使用取决于业务需要，不改变 6.2 节的强制要求，也不构成 Draft 2020-12 全部关键字的白名单。

| key（位于对应字段的 Schema 内） | 值类型             | 适用数据             | 说明                                                        |
| --------------------- | --------------- | ---------------- | --------------------------------------------------------- |
| `enum`                | 非空 array，元素不应重复 | 各类型              | 数据值应等于数组中的某个候选值；应说明每个候选值的业务含义                            |
| `const`               | 任意 JSON 值       | 各类型              | 数据值应等于指定常量；如 `accepted` 使用 `const: true` 表示成功响应中只能为 true |
| `default`             | 任意 JSON 值       | 各类型              | 说明建议默认值，不要求校验器或服务自动填充；实际缺省处理须在 `description` 中约定          |
| `minimum`             | number          | number / integer | 允许的最小值，包含边界；数值的业务单位应在字段说明中给出                              |
| `maximum`             | number          | number / integer | 允许的最大值，包含边界                                               |
| `minLength`           | 非负 integer      | string           | 字符串最少 Unicode 码点数，不是编码后的字节数                               |
| `maxLength`           | 非负 integer      | string           | 字符串最多 Unicode 码点数                                         |
| `minItems`            | 非负 integer      | array            | 数组最少元素数；需要禁止空数组时可设置为 1                                    |
| `maxItems`            | 非负 integer      | array            | 数组最多元素数，不限制单个元素内部字段的长度                                    |

### 6.5 描述格式与编写要求

#### 6.5.1 统一格式

方法级 `description` 及 `properties` 下业务字段的 `description` 应统一采用以下字符串格式，不新增独立的用户描述字段：

```text
用户描述&详细描述
```

| 组成部分 | 面向对象 | 内容要求 |
| --- | --- | --- |
| `&` 前的用户描述 | 最终用户、界面阅读者 | 简洁说明方法用途或参数含义，适合作为界面展示文字，例如“匹配文件列表” |
| 分隔符 `&` | 描述生成方及解析方 | 使用半角字符 `&`（U+0026）；按字符串中第一个 `&` 划分两部分，不应使用全角 `＆` 替代 |
| `&` 后的详细描述 | 开发、集成、运维人员及需要查看详情的用户 | 说明行为、取值约束、单位、缺省处理、边界情况或其他使用细节 |

两部分去除首尾空白后均应非空。用户描述中不应包含 `&`；详细描述中可包含后续 `&` 字符，解析时不应再次拆分。分隔符两侧不宜添加空格。分隔规则在 JSON 解码后执行，传输时仍使用普通 JSON 字符串，不采用额外转义约定。

界面默认可展示用户描述，详情区域可展示详细描述；输入校验仍以 Schema 的类型、必填和约束关键字为准，不应依赖拆解自然语言说明执行校验。错误返回的 `error.message` 不适用本节分隔格式。

示例：

```json
{
  "description": "匹配文件列表&无匹配项时为空数组。实际条数不超过本次请求的有效 maxResults。"
}
```

其中，“匹配文件列表”为面向用户的描述；“无匹配项时为空数组。实际条数不超过本次请求的有效 maxResults。”为详细描述。

#### 6.5.2 描述内容

每个业务 key 的 `description` 应使调用方能够理解“这个字段表示什么、如何填或如何解读”。涉及单位、坐标系、编码表、标识作用域、空值、空数组、默认行为或状态阶段时，应在说明中明确相关约定。对象和数组字段本身需要说明，其内部每个业务字段也需要单独说明。

例如 `results` 说明列表整体含义及空列表语义，`results[].path` 说明单个路径的含义与格式；只写“结果列表”“字符串”不足以替代具体业务说明。Schema 关键字的含义由 6.4 节统一解释，无需为 `type`、`required` 等关键字另加同名说明字段。

## 7 方法发现接口

### 7.1 接口标识与边界

接口操作名固定为 `listMethod`，区分大小写。它是协议内建发现操作，不属于业务方法命名空间，因此不要求添加 `Get_` 前缀，也不应作为业务方法注册到其自身返回列表。

业务方法名称检查的唯一例外是这里明确规定的内建发现操作；业务提供方不应以“内建”为由自行添加例外。

本版本一次返回当前调用方可见范围内、满足筛选条件的完整方法集合，不分页、不静默截断。目录过大无法完整返回时，应返回错误。以后引入分页须另行定义协议版本及分页一致性规则。

### 7.2 请求参数

请求业务参数应为对象，无筛选条件时传入 `{}`。

| 字段路径（key） | 类型     | 必填  | 含义                                        |
| --------- | ------ | --- | ----------------------------------------- |
| `service` | string | 否   | 请求对象的一级字段，按服务名筛选；精确匹配，符合 5.1 节；省略表示不限制服务名 |
| `method`  | string | 否   | 请求对象的一级字段，按方法名筛选；精确匹配，符合 5.2 节；省略表示不限制方法名 |

两者同时提供时按 AND 匹配；只提供 `method` 时，在可见服务中查找该名称，并分别归入所属服务分组。服务分组内仅包含满足本次筛选条件的方法。不支持模糊匹配、通配符和空字符串；不应传入未知参数。

例如，发现日志服务的方法；成功时仅返回 `Base_Log` 服务分组及其中的匹配方法：

```json
{
  "service": "Base_Log"
}
```

### 7.3 成功返回

成功返回应按服务分组，结构如下：

```json
{
  "specVersion": "1.0.0",
  "services": []
}
```

表 3 — 发现成功返回字段及层级

| 字段路径（key） | 类型 | 必填 | 含义与约束 |
| --- | --- | --- | --- |
| `specVersion` | string | 是 | 一级字段；方法描述及发现协议版本，本版本固定为 `1.0.0`，不表示业务服务版本或目录修订号 |
| `services` | array of object | 是 | 一级字段；完整的匹配服务分组清单。无匹配方法时为 `[]`；每个元素为第 6 章规定的服务描述对象 |
| `services[].service` | string | 是 | 服务分组中的服务名，同一返回中不应重复 |
| `services[].methods` | array of object | 是 | 当前服务下的匹配方法清单，不能为空；每个元素为第 6 章规定的方法描述对象 |
| `services[].methods[].method` | string | 是 | 方法名，仅在所属服务内要求唯一 |
| `services[].methods[].description` | string | 是 | 以“用户描述&详细描述”表达方法用途、行为和限制，格式见 6.5 节 |
| `services[].methods[].inputSchema` | object | 是 | 方法输入契约，内部 key 见 6.4 节 |
| `services[].methods[].outputSchema` | object 或 null | 是 | 方法输出契约；单向消息为 `null`，内部 key 见 6.4 节 |

成功返回顶层仅允许 `specVersion` 和 `services`。完整字段层级如下：

```text
成功返回对象 / Success Response
├── specVersion
└── services[]
    ├── service
    └── methods[]
        ├── method
        ├── description
        ├── inputSchema
        └── outputSchema
```

返回应符合下列要求：

a) 应返回匹配方法的完整描述，包括输入和输出 Schema，不应仅返回方法名。

b) 应先按请求条件筛选方法，再按所属服务分组；只返回存在匹配方法的服务，不应返回 `methods: []` 的空服务分组。

c) 不存在可见匹配方法时，应返回 `{"specVersion":"1.0.0","services":[]}`，不应返回 `null` 或“未找到”错误。

d) `services` 应按 `service` 的 ASCII 升序排列；各服务的 `methods` 应按 `method` 的 ASCII 升序排列。同一服务不应拆成多个分组，同一分组内不应出现重复方法名。

e) 同一次返回应基于一个逻辑一致的目录快照，不应混合某个方法更新前后的定义。

f) 只应返回当前调用方可发现的方法；可发现不代表已获得调用权限。

g) 返回前应完成描述校验。目录内存在无效描述或冲突时，应阻止其发布；若已影响本次返回集合，应返回目录错误，不应悄悄略过并宣称返回完整列表。

### 7.4 错误返回

发现操作失败时，应用层错误对象固定为：

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "service 应是符合命名规则的非空字符串"
  }
}
```

错误返回顶层仅允许 `error`；`error` 仅包含必填的字符串字段 `code` 和非空 `message`。成功对象与错误对象互斥，不应同时包含 `services` 和 `error`。

| 字段路径（key）       | 类型     | 必填  | 含义与层级                                                  |
| --------------- | ------ | --- | ------------------------------------------------------ |
| `error`         | object | 是   | 错误返回的一级字段，承载本次发现操作的失败信息                                |
| `error.code`    | string | 是   | `error` 内的二级字段；供程序判断错误类别，取值见下表                         |
| `error.message` | string | 是   | `error` 内的二级字段；供人阅读的非空错误说明，应说明具体失败原因，程序应使用 `code` 判断类别 |

| code                | 含义                    |
| ------------------- | --------------------- |
| `INVALID_ARGUMENT`  | 参数类型、命名、字段或筛选值不合法     |
| `UNAUTHENTICATED`   | 当前发现操作要求身份认证，但身份缺失或无效 |
| `PERMISSION_DENIED` | 当前身份没有执行发现操作的权限       |
| `CATALOG_INVALID`   | 待返回目录含无效描述或重复、冲突标识    |
| `CATALOG_TOO_LARGE` | 无法一次完整返回目录            |
| `INTERNAL_ERROR`    | 其他内部错误                |

无权执行发现操作时返回权限错误；有权发现但没有任何可见匹配项时返回成功空列表。业务方法调用的错误模型由调用协议另行定义。

具体传输协议应明确承载位置。例如采用 JSON-RPC 时，本节成功对象作为其 `result`；本节错误的 `code` 可映射到 JSON-RPC 错误 `data.code`，不应直接将字符串写入要求数值类型的协议错误码字段。本文不规定该映射的具体数值。

## 8 校验与发布要求

服务提供方在注册或更新描述时，应依次执行以下检查：

1. JSON 语法正确，不应含注释、尾随逗号或重复对象键。
2. 服务描述对象仅包含 `service`、`methods`；方法描述对象仅包含 `method`、`description`、`inputSchema`、`outputSchema`，字段齐全、类型正确且无额外字段。
3. 服务名、方法名的字符、长度和前缀符合要求；递归检查所有 `properties` 下的参数名符合 5.5 节，并确认 `required` 与其完全一致。
4. 同一目录内 `(service, method)` 唯一，实例之间定义一致；发现返回中服务名不重复、分组非空、方法归属正确且排序符合要求。
5. Schema 通过 Draft 2020-12 元 Schema 校验，并通过本规范额外约束检查；仅通过元 Schema 校验不足以证明完全符合本规范。
6. 所有本地引用能够解析；前缀与输出是否为 null 的约定一致。
7. 方法级及各业务字段的 `description` 包含半角分隔符 `&`，按第一个分隔符拆分后两部分均非空；方法级说明的总长度符合 6.1 节。
8. 示例载荷、实际参数及成功结果满足相应 Schema；跨字段、跨请求响应和业务语义约束另行检查。

任一强制检查失败，应拒绝该描述发布或更新，并保留此前有效目录。调用接收方应校验输入；提供方应保证输出符合发布定义。对单向消息，发布方应保证载荷符合 `inputSchema`，接收方宜校验载荷。

## 9 版本与兼容性

`specVersion` 采用 `主版本.次版本.修订版本`：破坏已有报文约定时提升主版本；兼容增加协议能力时提升次版本；不改变有效报文集合的文字澄清或勘误提升修订版本。当前实现应识别 `1.0.0`，不应自动假定未来版本可兼容。

业务方法兼容性应同时考虑请求和响应两个方向：

| 变更                       | 判定或注意事项                                           |
| ------------------------ | ------------------------------------------------- |
| 修改服务名、方法名、前缀或业务含义        | 破坏性变更                                             |
| 请求新增必填字段、删除原有可用字段、收紧取值范围 | 破坏性变更                                             |
| 请求新增可选字段                 | 旧客户端调用新服务通常兼容；新客户端调用旧服务仍可能失败                      |
| 响应删除字段、改变类型或扩大原有取值范围     | 可能破坏已有客户端                                         |
| 响应新增字段                   | 旧客户端在 `additionalProperties: false` 时会拒绝，不能默认视为兼容 |
| 仅补充不改变业务含义的说明或示例         | 通常兼容                                              |

同一 `(service, method)` 不应直接发布破坏性定义更新。需要并存时，应发布新的业务标识，例如 `Get_SearchFilesV2`，或在部署及注册层采用独立业务版本命名空间；迁移方案须由业务协议明确。

本草案定稿前的返回结构统一为 `services[].methods[]`。此前草案中的顶层扁平 `methods[]` 及方法内重复的 `service` 不属于本版有效格式，实现方应同步调整解析和生成逻辑；不应混用两种结构。若此前结构已作为正式协议发布，应按破坏性变更规则另行确定主版本，不应直接覆盖已发布协议。

## 10 符合性检查

表 4 — 符合性检查项目

| 编号 | 检查项目 | 预期结果 |
| --- | --- | --- |
| 01 | 服务名为 `Loco_Robot`、`Loco_Robot_Navigation` | 通过 |
| 02 | 服务名为 `LocoRobot`、`loco_Robot`、`Loco__Robot`、`Loco_Robot_` 或超过 64 个字符 | 拒绝 |
| 03 | 方法名为 `Get_SearchFiles` | 通过 |
| 04 | 方法名为 `SearchFiles`、`get_SearchFiles`、`Get__SearchFiles`、`Get_searchFiles` | 拒绝 |
| 05 | 同服务同方法重复，或相同服务拆为多个分组 | 拒绝 |
| 06 | 不同服务中出现相同方法名，且各自定义有效 | 通过 |
| 07 | `Get_`、`Cnr_` 的 `outputSchema` 为 null | 拒绝 |
| 08 | `Ntf_`、`Et_`、`Dat_` 的 `outputSchema` 非 null | 拒绝 |
| 09 | `required` 引用未定义字段、本地引用不能解析或字段说明全为空白 | 拒绝 |
| 10 | 无可见匹配方法 | 返回 `{"specVersion":"1.0.0","services":[]}` |
| 11 | 无效筛选参数 | 返回 `INVALID_ARGUMENT` |
| 12 | 目录过大，无法完整返回 | 返回 `CATALOG_TOO_LARGE`，不应返回部分清单 |
| 13 | 同一服务有多个匹配方法 | 一个服务分组包含全部匹配方法；`service` 仅在父对象出现一次 |
| 14 | 方法对象重复设置 `service`，或成功返回使用顶层 `methods` | 拒绝 |
| 15 | 服务分组包含空 `methods` 数组，或服务、方法排序错误 | 拒绝 |
| 16 | 同时按服务名和方法名筛选 | 仅返回该服务分组中的匹配方法；无匹配项时返回空服务清单 |
| 17 | 只按方法名筛选，多个服务存在该方法 | 分别返回各服务分组，每组只包含匹配方法 |
| 18 | 方法或业务字段的 `description` 不含 `&`，仅使用全角 `＆`，或任一部分为空白 | 拒绝 |
| 19 | `description` 为 `匹配文件列表&无匹配项时为空数组。` | 通过；用户描述为“匹配文件列表”，其余为详细描述 |
| 20 | `properties` 下参数名为 `maxResults`、`targetId`、`joint1Angle` | 通过 |
| 21 | 任意层级参数名为 `MaxResults`、`max_results`、`target-id`、`1stTarget`、中文或超过 64 个字符 | 拒绝 |
| 22 | `required` 的参数名与 `properties` 仅大小写不同 | 拒绝 |

## 附录 A（资料性） listMethod 返回示例与字段说明

### A.1 完整返回报文

以下示例按服务分组展示两个服务、三个方法。`Loco_Robot` 的两个方法共用父对象中的 `service`，方法对象不再重复携带服务名；服务和方法均已按规定排序。

```json
{
  "specVersion": "1.0.0",
  "services": [
    {
      "service": "Base_File",
      "methods": [
        {
          "method": "Get_SearchFiles",
          "description": "检索文件&按查询字符串检索文件并返回匹配路径；不修改文件。未传 maxResults 时按 20 条处理。",
          "inputSchema": {
            "type": "object",
            "properties": {
              "query": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1024,
                "description": "查询内容&用于文件检索的查询字符串，长度为 1～1024 个 Unicode 码点。"
              },
              "maxResults": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 20,
                "description": "最大结果数&最多返回的结果条数，取值为 1～100；省略时服务端按 20 处理。"
              }
            },
            "required": [
              "query"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "properties": {
              "results": {
                "type": "array",
                "maxItems": 100,
                "description": "匹配文件列表&无匹配项时为空数组。实际条数不超过本次请求的有效 maxResults。",
                "items": {
                  "type": "object",
                  "properties": {
                    "path": {
                      "type": "string",
                      "minLength": 1,
                      "description": "文件路径&文件在该服务逻辑根目录下的非空相对路径，使用 / 分隔，不含 .. 路径段。"
                    }
                  },
                  "required": [
                    "path"
                  ],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "results"
            ],
            "additionalProperties": false
          }
        }
      ]
    },
    {
      "service": "Loco_Robot",
      "methods": [
        {
          "method": "Cnr_SetWorkMode",
          "description": "设置工作模式&将机器人切换到指定工作模式；manual 表示手动模式，auto 表示自动模式。成功响应表示切换已完成；不满足切换条件或执行失败时，由调用协议返回错误，不返回成功结果。",
          "inputSchema": {
            "type": "object",
            "properties": {
              "workMode": {
                "type": "string",
                "enum": [
                  "manual",
                  "auto"
                ],
                "description": "目标工作模式&manual 表示手动模式，auto 表示自动模式；请求将机器人切换到指定模式。"
              }
            },
            "required": [
              "workMode"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "properties": {
              "currentMode": {
                "type": "string",
                "enum": [
                  "manual",
                  "auto"
                ],
                "description": "当前工作模式&切换完成后的实际工作模式，应与本次请求的 workMode 一致；返回成功结果表示切换已完成。"
              }
            },
            "required": [
              "currentMode"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Et_EmergencyStopTriggered",
          "description": "急停触发事件&机器人检测到急停由未触发变为触发时上报一次事件，携带触发来源和发生时间；持续处于触发状态不重复上报。本事件无业务响应，也不表示急停已解除。",
          "inputSchema": {
            "type": "object",
            "properties": {
              "triggerSource": {
                "type": "string",
                "enum": [
                  "physicalButton",
                  "externalInput"
                ],
                "description": "急停触发来源&physicalButton 表示实体急停按钮，externalInput 表示外部急停输入信号。"
              },
              "occurredAt": {
                "type": "integer",
                "minimum": 0,
                "description": "事件发生时间&急停触发时的 Unix 时间戳，单位为毫秒，以 UTC 1970-01-01T00:00:00Z 为起点；不是事件接收时间。"
              }
            },
            "required": [
              "triggerSource",
              "occurredAt"
            ],
            "additionalProperties": false
          },
          "outputSchema": null
        }
      ]
    }
  ]
}
```

示例中的工作模式、模式切换条件及急停触发来源用于说明格式，不构成对实际机器人控制协议或安全功能的定义。依赖请求内容的输出约束，如结果数不应超过请求的 `maxResults`，须由业务逻辑额外校验。

### A.2 示例业务 key 逐项说明

下表按“服务 → 方法 → 输入/输出 → 业务字段”的层级解释 A.1 示例。表中路径是实际业务数据的路径；对应 Schema 定义位于该方法的 `inputSchema` 或 `outputSchema` 内。

#### A.2.1 Base_File.Get_SearchFiles：文件查询

| 所属对象      | 业务字段路径           | 类型              | 必填         | 说明与约束                                              |
| --------- | ---------------- | --------------- | ---------- | -------------------------------------------------- |
| 输入参数      | `query`          | string          | 是          | 文件检索查询字符串，长度为 1～1024 个 Unicode 码点                  |
| 输入参数      | `maxResults`     | integer         | 否          | 本次最多返回的结果条数，范围为 1～100；省略时服务端按 20 处理                |
| 输出结果      | `results`        | array of object | 是          | 匹配文件列表；无匹配项时为 `[]`，最多 100 项，且不应超过本次有效 `maxResults` |
| 输出结果的数组元素 | `results[].path` | string          | 是，每个元素均须提供 | 服务逻辑根目录下的非空相对路径，使用 `/` 分隔，不含 `..` 路径段              |

`results` 的 `items` 定义每个数组元素的对象结构；元素内部的 `required: ["path"]` 仅约束该元素。路径格式和与请求 `maxResults` 的关联限制还须由业务逻辑校验。

#### A.2.2 Loco_Robot.Cnr_SetWorkMode：设置工作模式

本例展示可在一次请求—响应内完成的控制操作，成功响应阶段明确为“切换完成”，不引入异步任务标识或后续完成事件。`manual`、`auto` 分别表示手动模式和自动模式；具体切换前置条件由业务协议定义。

| 所属对象 | 业务字段路径 | 类型 | 必填 | 说明与约束 |
| --- | --- | --- | --- | --- |
| 输入参数 | `workMode` | string | 是 | 目标工作模式，仅允许 `manual` 或 `auto` |
| 输出结果 | `currentMode` | string | 是 | 切换完成后的实际工作模式，仅允许 `manual` 或 `auto`，且应与本次请求的 `workMode` 一致 |

实际调用的业务参数示例：

```json
{
  "workMode": "auto"
}
```

成功响应的业务结果示例：

```json
{
  "currentMode": "auto"
}
```

`currentMode` 与请求 `workMode` 的一致性应由业务逻辑校验。请求不合法、不满足切换条件或切换失败时，由调用协议表达错误，不应返回上述成功结果；本例不定义业务错误码。

#### A.2.3 Loco_Robot.Et_EmergencyStopTriggered：急停触发事件

本例展示已经发生的离散业务事件。发布方在检测到急停从未触发变为触发时上报，持续触发期间不重复上报；它不是用于执行急停动作的控制请求，也不是持续状态的周期上报。

| 所属对象 | 业务字段路径 | 类型 | 必填 | 说明与约束 |
| --- | --- | --- | --- | --- |
| 事件载荷 | `triggerSource` | string | 是 | 触发来源：`physicalButton` 表示实体急停按钮，`externalInput` 表示外部急停输入信号 |
| 事件载荷 | `occurredAt` | integer | 是 | 事件发生时的 Unix 时间戳，单位为毫秒，自 UTC 1970-01-01T00:00:00Z 起计，且不小于 0；不是接收时间 |

实际发布的事件业务载荷示例：

```json
{
  "triggerSource": "physicalButton",
  "occurredAt": 1795046400000
}
```

事件字段由发布方填写，订阅或接收方读取。该方法的 `inputSchema` 用于校验事件载荷，不表示接收方应主动调用该方法；`outputSchema` 为 `null`，不定义业务返回值。事件传递及订阅方式由具体传输绑定规定。
