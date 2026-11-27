# 附录 A listMethod 返回示例与字段说明

本附录由当前实现的 `listMethod({})` 直接生成，描述4个服务、23个方法。不是调用请求，也不是 GUI 导出日志的外壳。
业务方法的名称属于本项目约定；企业附录中的 Base_File、Loco_Robot 是格式示例，不要求实现相同业务。
输入、输出及字段说明与实际发现响应一致；生成快照不会启动服务或连接现场设备。

## A.1 完整返回报文

以下为不带筛选条件的完整成功响应。可直接下载 [JSON 原文件](listMethod-response.json)。

```json
{
  "specVersion": "1.0.0",
  "services": [
    {
      "service": "Mesh_Admission",
      "methods": [
        {
          "method": "Cnr_SetTrustStatus",
          "description": "Manage trust&Success persists admission; broker ACL still requires controlled reload.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "trustStatus": {
                "type": "string",
                "description": "信任状态&pending, trusted or revoked admission decision.",
                "enum": [
                  "pending",
                  "trusted",
                  "revoked"
                ]
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "trustStatus",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "trustStatus": {
                "type": "string",
                "description": "信任状态&pending, trusted or revoked admission decision.",
                "maxLength": 256
              },
              "admissionRevision": {
                "type": "integer",
                "description": "Admission revision&Admission decision revision, distinct from task or parent policy revision.",
                "minimum": 0
              },
              "brokerAclApplied": {
                "type": "boolean",
                "description": "Broker acl applied&Whether broker enforcement has been applied; current adapter returns false."
              },
              "brokerAclReloadRequired": {
                "type": "boolean",
                "description": "Broker acl reload required&Whether the generated pending broker ACL still needs controlled loading."
              }
            },
            "required": [],
            "additionalProperties": false
          }
        }
      ]
    },
    {
      "service": "Mesh_Node",
      "methods": [
        {
          "method": "Cnr_Echo",
          "description": "Echo text&Success means the device returned the input text.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "text": {
                "type": "string",
                "description": "回显文本&Text sent to or returned by the diagnostic echo operation.",
                "maxLength": 256
              }
            },
            "required": [
              "text"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "text": {
                "type": "string",
                "description": "回显文本&Text sent to or returned by the diagnostic echo operation.",
                "maxLength": 256
              }
            },
            "required": [
              "text"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_Ping",
          "description": "Probe device&Success means a matching application acknowledgement.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "acknowledged": {
                "type": "boolean",
                "description": "Acknowledged&True only after a matching successful application ACK.",
                "const": true
              }
            },
            "required": [
              "acknowledged"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_NodeList",
          "description": "List nodes&Returns observed readiness and radio snapshots.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "nodes": {
                "type": "array",
                "description": "节点清单&Registered or observed nodes; historical entries do not prove current connectivity.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "nodeId": {
                      "type": "string",
                      "description": "Node id&Identity of the node described by this record.",
                      "maxLength": 256
                    },
                    "role": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Role&Configured device role in the four-level mesh."
                    },
                    "rootId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Root id&Managing root node identity."
                    },
                    "trustStatus": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "信任状态&pending, trusted or revoked admission decision."
                    },
                    "ready": {
                      "type": "boolean",
                      "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                    },
                    "enabled": {
                      "type": "boolean",
                      "description": "Enabled&Whether the administrator enabled the inventory entry."
                    },
                    "admissionRevision": {
                      "type": "integer",
                      "description": "Admission revision&Admission decision revision, distinct from task or parent policy revision.",
                      "minimum": 0
                    },
                    "online": {
                      "type": [
                        "boolean",
                        "null"
                      ],
                      "description": "Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee."
                    },
                    "statusAgeS": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Status age s&Telemetry age in seconds, or null if unreported."
                    },
                    "statusCurrentBoot": {
                      "type": "boolean",
                      "description": "Status current boot&Whether telemetry belongs to the currently observed boot."
                    },
                    "operations": {
                      "type": "array",
                      "description": "Operations&Announced supported operations.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "taskTypes": {
                      "type": "array",
                      "description": "Task types&Announced supported task types.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "status": {
                      "type": [
                        "object",
                        "null"
                      ],
                      "description": "Status&Observed device state or null if no observation exists.",
                      "properties": {
                        "role": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Role&Configured device role in the four-level mesh."
                        },
                        "topology": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Topology&Configured Mesh topology."
                        },
                        "staIp": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Sta ip&Observed station IPv4 address."
                        },
                        "apIp": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                        },
                        "gateway": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Gateway&Observed station default gateway IPv4 address."
                        },
                        "netmask": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Netmask&Observed IPv4 netmask."
                        },
                        "staMac": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Sta mac&Station MAC address."
                        },
                        "apMac": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap mac&AP MAC address; absent when AP is disabled."
                        },
                        "apSsid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap ssid&Advertised AP SSID."
                        },
                        "parentBssid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                        },
                        "executionHost": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Execution host&local identifies the host task service rather than a physical radio."
                        },
                        "level": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Level&Observed Mesh level."
                        },
                        "heap": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap&Current free heap in bytes."
                        },
                        "heapMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap min&Minimum free heap in bytes."
                        },
                        "uptimeMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                        },
                        "rssi": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                        },
                        "channel": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Channel&Wi-Fi channel number."
                        },
                        "associatedChildren": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                        },
                        "apEnabled": {
                          "type": "boolean",
                          "description": "Ap enabled&Whether this device actually has AP mode enabled."
                        },
                        "parentConnected": {
                          "type": "boolean",
                          "description": "Parent connected&Whether the device reports association to an upstream AP."
                        },
                        "parentPolicy": {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "mode": {
                              "type": "string",
                              "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                              "maxLength": 256
                            },
                            "revision": {
                              "type": "integer",
                              "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                              "minimum": 0
                            },
                            "parentNodeId": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                            },
                            "stage": {
                              "type": "string",
                              "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                              "maxLength": 256
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        },
                        "networkStatus": {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "status": {
                              "type": "object",
                              "description": "Status&Observed device state or null if no observation exists.",
                              "properties": {
                                "role": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Role&Configured device role in the four-level mesh."
                                },
                                "topology": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Topology&Configured Mesh topology."
                                },
                                "staIp": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Sta ip&Observed station IPv4 address."
                                },
                                "apIp": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                                },
                                "gateway": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Gateway&Observed station default gateway IPv4 address."
                                },
                                "netmask": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Netmask&Observed IPv4 netmask."
                                },
                                "staMac": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Sta mac&Station MAC address."
                                },
                                "apMac": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap mac&AP MAC address; absent when AP is disabled."
                                },
                                "apSsid": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap ssid&Advertised AP SSID."
                                },
                                "parentBssid": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                                },
                                "executionHost": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Execution host&local identifies the host task service rather than a physical radio."
                                },
                                "level": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Level&Observed Mesh level."
                                },
                                "heap": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Heap&Current free heap in bytes."
                                },
                                "heapMin": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Heap min&Minimum free heap in bytes."
                                },
                                "uptimeMs": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                                },
                                "rssi": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                                },
                                "channel": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Channel&Wi-Fi channel number."
                                },
                                "associatedChildren": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                                },
                                "apEnabled": {
                                  "type": "boolean",
                                  "description": "Ap enabled&Whether this device actually has AP mode enabled."
                                },
                                "parentConnected": {
                                  "type": "boolean",
                                  "description": "Parent connected&Whether the device reports association to an upstream AP."
                                },
                                "parentPolicy": {
                                  "type": "object",
                                  "description": "Business record&Fields follow the published method contract.",
                                  "properties": {
                                    "mode": {
                                      "type": "string",
                                      "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                                      "maxLength": 256
                                    },
                                    "revision": {
                                      "type": "integer",
                                      "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                                      "minimum": 0
                                    },
                                    "parentNodeId": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                                    },
                                    "stage": {
                                      "type": "string",
                                      "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                                      "maxLength": 256
                                    }
                                  },
                                  "required": [],
                                  "additionalProperties": false
                                }
                              },
                              "required": [],
                              "additionalProperties": false
                            },
                            "ageS": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Age s&Valid feedback or snapshot age in seconds."
                            },
                            "fresh": {
                              "type": "boolean",
                              "description": "Fresh&Whether the root USB network snapshot is within its freshness window."
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    },
                    "parentPolicy": {
                      "type": "object",
                      "description": "Business record&Fields follow the published method contract.",
                      "properties": {
                        "mode": {
                          "type": "string",
                          "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                          "maxLength": 256
                        },
                        "parentNodeId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                        },
                        "revision": {
                          "type": "integer",
                          "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                          "minimum": 0
                        },
                        "state": {
                          "type": "string",
                          "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed.",
                          "maxLength": 256
                        },
                        "error": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Error&Known operation or execution error; null means no recorded error."
                        },
                        "actualBssid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy."
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "nodes"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_RegisteredNodes",
          "description": "Registration history&Does not establish live connectivity.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "nodes": {
                "type": "array",
                "description": "节点清单&Registered or observed nodes; historical entries do not prove current connectivity.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "nodeId": {
                      "type": "string",
                      "description": "Node id&Identity of the node described by this record.",
                      "maxLength": 256
                    },
                    "rootId": {
                      "type": "string",
                      "description": "Root id&Managing root node identity.",
                      "maxLength": 256
                    },
                    "registered": {
                      "type": "boolean",
                      "description": "Registered&Whether this historical catalog entry is still in the administrator inventory."
                    },
                    "observedAt": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Observed at&Host observation time as Unix seconds or null if unknown."
                    },
                    "registration": {
                      "type": "object",
                      "description": "Registration&Administrator registration snapshot; observations cannot grant trust.",
                      "properties": {
                        "nodeId": {
                          "type": "string",
                          "description": "Node id&Identity of the node described by this record.",
                          "maxLength": 256
                        },
                        "rootId": {
                          "type": "string",
                          "description": "Root id&Managing root node identity.",
                          "maxLength": 256
                        },
                        "role": {
                          "type": "string",
                          "description": "Role&Configured device role in the four-level mesh.",
                          "maxLength": 256
                        },
                        "enabled": {
                          "type": "boolean",
                          "description": "Enabled&Whether the administrator enabled the inventory entry."
                        },
                        "apSubnet": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Ap subnet&Reserved 192.168.N.0/24 AP subnet index; null for STA-only leaves."
                        },
                        "trustStatus": {
                          "type": "string",
                          "description": "信任状态&pending, trusted or revoked admission decision.",
                          "maxLength": 256
                        },
                        "admissionRevision": {
                          "type": "integer",
                          "description": "Admission revision&Admission decision revision, distinct from task or parent policy revision.",
                          "minimum": 0
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    },
                    "lastObservation": {
                      "type": [
                        "object",
                        "null"
                      ],
                      "description": "Last observation&Last stored node snapshot or null when none has been recorded.",
                      "properties": {
                        "nodeId": {
                          "type": "string",
                          "description": "Node id&Identity of the node described by this record.",
                          "maxLength": 256
                        },
                        "role": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Role&Configured device role in the four-level mesh."
                        },
                        "rootId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Root id&Managing root node identity."
                        },
                        "trustStatus": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "信任状态&pending, trusted or revoked admission decision."
                        },
                        "ready": {
                          "type": "boolean",
                          "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                        },
                        "enabled": {
                          "type": "boolean",
                          "description": "Enabled&Whether the administrator enabled the inventory entry."
                        },
                        "admissionRevision": {
                          "type": "integer",
                          "description": "Admission revision&Admission decision revision, distinct from task or parent policy revision.",
                          "minimum": 0
                        },
                        "online": {
                          "type": [
                            "boolean",
                            "null"
                          ],
                          "description": "Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee."
                        },
                        "statusAgeS": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Status age s&Telemetry age in seconds, or null if unreported."
                        },
                        "statusCurrentBoot": {
                          "type": "boolean",
                          "description": "Status current boot&Whether telemetry belongs to the currently observed boot."
                        },
                        "operations": {
                          "type": "array",
                          "description": "Operations&Announced supported operations.",
                          "items": {
                            "type": "string",
                            "description": "Business value&See the method contract for meaning and constraints.",
                            "maxLength": 256
                          }
                        },
                        "taskTypes": {
                          "type": "array",
                          "description": "Task types&Announced supported task types.",
                          "items": {
                            "type": "string",
                            "description": "Business value&See the method contract for meaning and constraints.",
                            "maxLength": 256
                          }
                        },
                        "status": {
                          "type": [
                            "object",
                            "null"
                          ],
                          "description": "Status&Observed device state or null if no observation exists.",
                          "properties": {
                            "role": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Role&Configured device role in the four-level mesh."
                            },
                            "topology": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Topology&Configured Mesh topology."
                            },
                            "staIp": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Sta ip&Observed station IPv4 address."
                            },
                            "apIp": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                            },
                            "gateway": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Gateway&Observed station default gateway IPv4 address."
                            },
                            "netmask": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Netmask&Observed IPv4 netmask."
                            },
                            "staMac": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Sta mac&Station MAC address."
                            },
                            "apMac": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Ap mac&AP MAC address; absent when AP is disabled."
                            },
                            "apSsid": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Ap ssid&Advertised AP SSID."
                            },
                            "parentBssid": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                            },
                            "executionHost": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Execution host&local identifies the host task service rather than a physical radio."
                            },
                            "level": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Level&Observed Mesh level."
                            },
                            "heap": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Heap&Current free heap in bytes."
                            },
                            "heapMin": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Heap min&Minimum free heap in bytes."
                            },
                            "uptimeMs": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                            },
                            "rssi": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                            },
                            "channel": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Channel&Wi-Fi channel number."
                            },
                            "associatedChildren": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                            },
                            "apEnabled": {
                              "type": "boolean",
                              "description": "Ap enabled&Whether this device actually has AP mode enabled."
                            },
                            "parentConnected": {
                              "type": "boolean",
                              "description": "Parent connected&Whether the device reports association to an upstream AP."
                            },
                            "parentPolicy": {
                              "type": "object",
                              "description": "Business record&Fields follow the published method contract.",
                              "properties": {
                                "mode": {
                                  "type": "string",
                                  "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                                  "maxLength": 256
                                },
                                "revision": {
                                  "type": "integer",
                                  "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                                  "minimum": 0
                                },
                                "parentNodeId": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                                },
                                "stage": {
                                  "type": "string",
                                  "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                                  "maxLength": 256
                                }
                              },
                              "required": [],
                              "additionalProperties": false
                            },
                            "networkStatus": {
                              "type": "object",
                              "description": "Business record&Fields follow the published method contract.",
                              "properties": {
                                "status": {
                                  "type": "object",
                                  "description": "Status&Observed device state or null if no observation exists.",
                                  "properties": {
                                    "role": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Role&Configured device role in the four-level mesh."
                                    },
                                    "topology": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Topology&Configured Mesh topology."
                                    },
                                    "staIp": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Sta ip&Observed station IPv4 address."
                                    },
                                    "apIp": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                                    },
                                    "gateway": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Gateway&Observed station default gateway IPv4 address."
                                    },
                                    "netmask": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Netmask&Observed IPv4 netmask."
                                    },
                                    "staMac": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Sta mac&Station MAC address."
                                    },
                                    "apMac": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Ap mac&AP MAC address; absent when AP is disabled."
                                    },
                                    "apSsid": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Ap ssid&Advertised AP SSID."
                                    },
                                    "parentBssid": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                                    },
                                    "executionHost": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "Execution host&local identifies the host task service rather than a physical radio."
                                    },
                                    "level": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Level&Observed Mesh level."
                                    },
                                    "heap": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Heap&Current free heap in bytes."
                                    },
                                    "heapMin": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Heap min&Minimum free heap in bytes."
                                    },
                                    "uptimeMs": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                                    },
                                    "rssi": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                                    },
                                    "channel": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Channel&Wi-Fi channel number."
                                    },
                                    "associatedChildren": {
                                      "type": [
                                        "number",
                                        "null"
                                      ],
                                      "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                                    },
                                    "apEnabled": {
                                      "type": "boolean",
                                      "description": "Ap enabled&Whether this device actually has AP mode enabled."
                                    },
                                    "parentConnected": {
                                      "type": "boolean",
                                      "description": "Parent connected&Whether the device reports association to an upstream AP."
                                    },
                                    "parentPolicy": {
                                      "type": "object",
                                      "description": "Business record&Fields follow the published method contract.",
                                      "properties": {
                                        "mode": {
                                          "type": "string",
                                          "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                                          "maxLength": 256
                                        },
                                        "revision": {
                                          "type": "integer",
                                          "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                                          "minimum": 0
                                        },
                                        "parentNodeId": {
                                          "type": [
                                            "string",
                                            "null"
                                          ],
                                          "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                                        },
                                        "stage": {
                                          "type": "string",
                                          "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                                          "maxLength": 256
                                        }
                                      },
                                      "required": [],
                                      "additionalProperties": false
                                    }
                                  },
                                  "required": [],
                                  "additionalProperties": false
                                },
                                "ageS": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Age s&Valid feedback or snapshot age in seconds."
                                },
                                "fresh": {
                                  "type": "boolean",
                                  "description": "Fresh&Whether the root USB network snapshot is within its freshness window."
                                }
                              },
                              "required": [],
                              "additionalProperties": false
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        },
                        "parentPolicy": {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "mode": {
                              "type": "string",
                              "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                              "maxLength": 256
                            },
                            "parentNodeId": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                            },
                            "revision": {
                              "type": "integer",
                              "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                              "minimum": 0
                            },
                            "state": {
                              "type": "string",
                              "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed.",
                              "maxLength": 256
                            },
                            "error": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Error&Known operation or execution error; null means no recorded error."
                            },
                            "actualBssid": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy."
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "nodes"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_ServiceInstances",
          "description": "List instances&Availability is separate from method discovery.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "instances": {
                "type": "array",
                "description": "服务实例&Runtime capability instances and their availability, separate from method definitions.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "serviceId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Service id&Legacy runtime instance identifier, not a stable MCI service name."
                    },
                    "nodeId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Node id&Identity of the node described by this record."
                    },
                    "agentType": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Agent type&Execution agent role."
                    },
                    "serviceType": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Service type&Legacy instance task type."
                    },
                    "availability": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Availability&Instance availability: available, busy or unavailable."
                    },
                    "taskStatus": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Task status&Last known instance execution state."
                    },
                    "taskId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                    },
                    "bootId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Boot id&Executor boot identity."
                    },
                    "executionMode": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition."
                    },
                    "reason": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Reason&Instance unavailability reason, or null when none."
                    },
                    "capabilities": {
                      "type": "array",
                      "description": "Capabilities&Announced instance capability labels.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "operations": {
                      "type": "array",
                      "description": "Operations&Announced supported operations.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "announced": {
                      "type": "boolean",
                      "description": "Announced&Whether the required runtime capability has been announced."
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "instances"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_Status",
          "description": "Read device status&Requires a ready authorized MQTT device.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "role": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Role&Configured device role in the four-level mesh."
              },
              "topology": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Topology&Configured Mesh topology."
              },
              "staIp": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Sta ip&Observed station IPv4 address."
              },
              "apIp": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
              },
              "gateway": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Gateway&Observed station default gateway IPv4 address."
              },
              "netmask": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Netmask&Observed IPv4 netmask."
              },
              "staMac": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Sta mac&Station MAC address."
              },
              "apMac": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Ap mac&AP MAC address; absent when AP is disabled."
              },
              "apSsid": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Ap ssid&Advertised AP SSID."
              },
              "parentBssid": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
              },
              "executionHost": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Execution host&local identifies the host task service rather than a physical radio."
              },
              "level": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Level&Observed Mesh level."
              },
              "heap": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Heap&Current free heap in bytes."
              },
              "heapMin": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Heap min&Minimum free heap in bytes."
              },
              "uptimeMs": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
              },
              "rssi": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
              },
              "channel": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Channel&Wi-Fi channel number."
              },
              "associatedChildren": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Associated children&Associated AP client count; absent for STA-only leaves."
              },
              "apEnabled": {
                "type": "boolean",
                "description": "Ap enabled&Whether this device actually has AP mode enabled."
              },
              "parentConnected": {
                "type": "boolean",
                "description": "Parent connected&Whether the device reports association to an upstream AP."
              },
              "parentPolicy": {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "mode": {
                    "type": "string",
                    "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                    "maxLength": 256
                  },
                  "revision": {
                    "type": "integer",
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                    "minimum": 0
                  },
                  "parentNodeId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                  },
                  "stage": {
                    "type": "string",
                    "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                    "maxLength": 256
                  }
                },
                "required": [],
                "additionalProperties": false
              },
              "networkStatus": {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "status": {
                    "type": "object",
                    "description": "Status&Observed device state or null if no observation exists.",
                    "properties": {
                      "role": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Role&Configured device role in the four-level mesh."
                      },
                      "topology": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Topology&Configured Mesh topology."
                      },
                      "staIp": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Sta ip&Observed station IPv4 address."
                      },
                      "apIp": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                      },
                      "gateway": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Gateway&Observed station default gateway IPv4 address."
                      },
                      "netmask": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Netmask&Observed IPv4 netmask."
                      },
                      "staMac": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Sta mac&Station MAC address."
                      },
                      "apMac": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Ap mac&AP MAC address; absent when AP is disabled."
                      },
                      "apSsid": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Ap ssid&Advertised AP SSID."
                      },
                      "parentBssid": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                      },
                      "executionHost": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Execution host&local identifies the host task service rather than a physical radio."
                      },
                      "level": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Level&Observed Mesh level."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "uptimeMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "channel": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Channel&Wi-Fi channel number."
                      },
                      "associatedChildren": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                      },
                      "apEnabled": {
                        "type": "boolean",
                        "description": "Ap enabled&Whether this device actually has AP mode enabled."
                      },
                      "parentConnected": {
                        "type": "boolean",
                        "description": "Parent connected&Whether the device reports association to an upstream AP."
                      },
                      "parentPolicy": {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "mode": {
                            "type": "string",
                            "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                            "maxLength": 256
                          },
                          "revision": {
                            "type": "integer",
                            "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                            "minimum": 0
                          },
                          "parentNodeId": {
                            "type": [
                              "string",
                              "null"
                            ],
                            "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                          },
                          "stage": {
                            "type": "string",
                            "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                            "maxLength": 256
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "ageS": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Age s&Valid feedback or snapshot age in seconds."
                  },
                  "fresh": {
                    "type": "boolean",
                    "description": "Fresh&Whether the root USB network snapshot is within its freshness window."
                  }
                },
                "required": [],
                "additionalProperties": false
              }
            },
            "required": [],
            "additionalProperties": false
          }
        },
        {
          "method": "Ntf_NodeSnapshot",
          "description": "Node snapshot&One-way periodic observation; not durable history.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "nodes": {
                "type": "array",
                "description": "节点清单&Registered or observed nodes; historical entries do not prove current connectivity.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "nodeId": {
                      "type": "string",
                      "description": "Node id&Identity of the node described by this record.",
                      "maxLength": 256
                    },
                    "role": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Role&Configured device role in the four-level mesh."
                    },
                    "rootId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Root id&Managing root node identity."
                    },
                    "trustStatus": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "信任状态&pending, trusted or revoked admission decision."
                    },
                    "ready": {
                      "type": "boolean",
                      "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                    },
                    "enabled": {
                      "type": "boolean",
                      "description": "Enabled&Whether the administrator enabled the inventory entry."
                    },
                    "admissionRevision": {
                      "type": "integer",
                      "description": "Admission revision&Admission decision revision, distinct from task or parent policy revision.",
                      "minimum": 0
                    },
                    "online": {
                      "type": [
                        "boolean",
                        "null"
                      ],
                      "description": "Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee."
                    },
                    "statusAgeS": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Status age s&Telemetry age in seconds, or null if unreported."
                    },
                    "statusCurrentBoot": {
                      "type": "boolean",
                      "description": "Status current boot&Whether telemetry belongs to the currently observed boot."
                    },
                    "operations": {
                      "type": "array",
                      "description": "Operations&Announced supported operations.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "taskTypes": {
                      "type": "array",
                      "description": "Task types&Announced supported task types.",
                      "items": {
                        "type": "string",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "maxLength": 256
                      }
                    },
                    "status": {
                      "type": [
                        "object",
                        "null"
                      ],
                      "description": "Status&Observed device state or null if no observation exists.",
                      "properties": {
                        "role": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Role&Configured device role in the four-level mesh."
                        },
                        "topology": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Topology&Configured Mesh topology."
                        },
                        "staIp": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Sta ip&Observed station IPv4 address."
                        },
                        "apIp": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                        },
                        "gateway": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Gateway&Observed station default gateway IPv4 address."
                        },
                        "netmask": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Netmask&Observed IPv4 netmask."
                        },
                        "staMac": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Sta mac&Station MAC address."
                        },
                        "apMac": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap mac&AP MAC address; absent when AP is disabled."
                        },
                        "apSsid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Ap ssid&Advertised AP SSID."
                        },
                        "parentBssid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                        },
                        "executionHost": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Execution host&local identifies the host task service rather than a physical radio."
                        },
                        "level": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Level&Observed Mesh level."
                        },
                        "heap": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap&Current free heap in bytes."
                        },
                        "heapMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap min&Minimum free heap in bytes."
                        },
                        "uptimeMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                        },
                        "rssi": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                        },
                        "channel": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Channel&Wi-Fi channel number."
                        },
                        "associatedChildren": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                        },
                        "apEnabled": {
                          "type": "boolean",
                          "description": "Ap enabled&Whether this device actually has AP mode enabled."
                        },
                        "parentConnected": {
                          "type": "boolean",
                          "description": "Parent connected&Whether the device reports association to an upstream AP."
                        },
                        "parentPolicy": {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "mode": {
                              "type": "string",
                              "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                              "maxLength": 256
                            },
                            "revision": {
                              "type": "integer",
                              "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                              "minimum": 0
                            },
                            "parentNodeId": {
                              "type": [
                                "string",
                                "null"
                              ],
                              "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                            },
                            "stage": {
                              "type": "string",
                              "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                              "maxLength": 256
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        },
                        "networkStatus": {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "status": {
                              "type": "object",
                              "description": "Status&Observed device state or null if no observation exists.",
                              "properties": {
                                "role": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Role&Configured device role in the four-level mesh."
                                },
                                "topology": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Topology&Configured Mesh topology."
                                },
                                "staIp": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Sta ip&Observed station IPv4 address."
                                },
                                "apIp": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap ip&Observed AP IPv4 address; absent for STA-only leaves."
                                },
                                "gateway": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Gateway&Observed station default gateway IPv4 address."
                                },
                                "netmask": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Netmask&Observed IPv4 netmask."
                                },
                                "staMac": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Sta mac&Station MAC address."
                                },
                                "apMac": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap mac&AP MAC address; absent when AP is disabled."
                                },
                                "apSsid": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Ap ssid&Advertised AP SSID."
                                },
                                "parentBssid": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Parent bssid&Observed parent AP MAC, not an inferred parent identity."
                                },
                                "executionHost": {
                                  "type": [
                                    "string",
                                    "null"
                                  ],
                                  "description": "Execution host&local identifies the host task service rather than a physical radio."
                                },
                                "level": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Level&Observed Mesh level."
                                },
                                "heap": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Heap&Current free heap in bytes."
                                },
                                "heapMin": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Heap min&Minimum free heap in bytes."
                                },
                                "uptimeMs": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Uptime ms&Device monotonic uptime in milliseconds; not UTC."
                                },
                                "rssi": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                                },
                                "channel": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Channel&Wi-Fi channel number."
                                },
                                "associatedChildren": {
                                  "type": [
                                    "number",
                                    "null"
                                  ],
                                  "description": "Associated children&Associated AP client count; absent for STA-only leaves."
                                },
                                "apEnabled": {
                                  "type": "boolean",
                                  "description": "Ap enabled&Whether this device actually has AP mode enabled."
                                },
                                "parentConnected": {
                                  "type": "boolean",
                                  "description": "Parent connected&Whether the device reports association to an upstream AP."
                                },
                                "parentPolicy": {
                                  "type": "object",
                                  "description": "Business record&Fields follow the published method contract.",
                                  "properties": {
                                    "mode": {
                                      "type": "string",
                                      "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                                      "maxLength": 256
                                    },
                                    "revision": {
                                      "type": "integer",
                                      "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                                      "minimum": 0
                                    },
                                    "parentNodeId": {
                                      "type": [
                                        "string",
                                        "null"
                                      ],
                                      "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                                    },
                                    "stage": {
                                      "type": "string",
                                      "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                                      "maxLength": 256
                                    }
                                  },
                                  "required": [],
                                  "additionalProperties": false
                                }
                              },
                              "required": [],
                              "additionalProperties": false
                            },
                            "ageS": {
                              "type": [
                                "number",
                                "null"
                              ],
                              "description": "Age s&Valid feedback or snapshot age in seconds."
                            },
                            "fresh": {
                              "type": "boolean",
                              "description": "Fresh&Whether the root USB network snapshot is within its freshness window."
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    },
                    "parentPolicy": {
                      "type": "object",
                      "description": "Business record&Fields follow the published method contract.",
                      "properties": {
                        "mode": {
                          "type": "string",
                          "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                          "maxLength": 256
                        },
                        "parentNodeId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
                        },
                        "revision": {
                          "type": "integer",
                          "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                          "minimum": 0
                        },
                        "state": {
                          "type": "string",
                          "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed.",
                          "maxLength": 256
                        },
                        "error": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Error&Known operation or execution error; null means no recorded error."
                        },
                        "actualBssid": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy."
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              },
              "brokerConnected": {
                "type": "boolean",
                "description": "Broker connected&Whether the local host is connected to Mosquitto."
              }
            },
            "required": [
              "nodes",
              "brokerConnected"
            ],
            "additionalProperties": false
          },
          "outputSchema": null
        }
      ]
    },
    {
      "service": "Mesh_Parent",
      "methods": [
        {
          "method": "Cnr_SetPolicy",
          "description": "Set parent policy&Accepted is not applied; fresh matching telemetry confirms application.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "mode": {
                "type": "string",
                "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                "enum": [
                  "auto",
                  "prefer",
                  "fixed"
                ]
              },
              "parentNodeId": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "mode",
              "parentNodeId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "mode": {
                "type": "string",
                "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                "maxLength": 256
              },
              "parentNodeId": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
              },
              "revision": {
                "type": "integer",
                "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                "minimum": 0
              },
              "state": {
                "type": "string",
                "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed.",
                "maxLength": 256
              },
              "error": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Error&Known operation or execution error; null means no recorded error."
              },
              "actualBssid": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy."
              }
            },
            "required": [],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_Policy",
          "description": "Read parent policy&Returns saved intent and available observation.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "mode": {
                "type": "string",
                "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.",
                "maxLength": 256
              },
              "parentNodeId": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "指定父节点&Desired parent UAV identity; null for automatic selection."
              },
              "revision": {
                "type": "integer",
                "description": "Revision&Current task or parent policy revision; these revision domains are independent.",
                "minimum": 0
              },
              "state": {
                "type": "string",
                "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed.",
                "maxLength": 256
              },
              "error": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Error&Known operation or execution error; null means no recorded error."
              },
              "actualBssid": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy."
              }
            },
            "required": [],
            "additionalProperties": false
          }
        }
      ]
    },
    {
      "service": "Mesh_Task",
      "methods": [
        {
          "method": "Cnr_CancelTask",
          "description": "取消任务&成功表示取消意图已受理；应查询并确认最终任务状态。",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_CreateTask",
          "description": "Create task&Persists CREATED; does not start execution.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "executorNodeId": {
                "type": "string",
                "description": "执行节点&Device or host selected to execute the created task.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "kind": {
                "type": "string",
                "description": "任务类型&Task type; selects the corresponding config and result contract.",
                "enum": [
                  "diagnostics",
                  "network_diagnostics",
                  "task_monitor",
                  "patrol",
                  "anomaly_review"
                ]
              },
              "config": {
                "type": "object",
                "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                "properties": {
                  "durationSeconds": {
                    "type": "integer",
                    "description": "Business value&See the method contract for meaning and constraints.",
                    "minimum": 1,
                    "maximum": 3600
                  },
                  "periodMs": {
                    "type": "integer",
                    "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                    "minimum": 200,
                    "maximum": 10000
                  },
                  "probeNodeId": {
                    "type": "string",
                    "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "watchTaskId": {
                    "type": "string",
                    "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "staleAfterSeconds": {
                    "type": "integer",
                    "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                    "minimum": 1,
                    "maximum": 3600
                  },
                  "executionMode": {
                    "type": "string",
                    "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                    "const": "esp32_test"
                  },
                  "areaId": {
                    "type": "string",
                    "description": "Area id&Logical test area identifier.",
                    "pattern": "^[A-Za-z0-9_-]{1,12}$"
                  },
                  "pointIds": {
                    "type": "array",
                    "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                    "items": {
                      "type": "string",
                      "description": "Business value&See the method contract for meaning and constraints.",
                      "pattern": "^[A-Za-z0-9_-]{1,12}$"
                    },
                    "minItems": 1,
                    "maxItems": 3,
                    "uniqueItems": true
                  },
                  "pointDurationSeconds": {
                    "type": "integer",
                    "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                    "minimum": 1,
                    "maximum": 60
                  },
                  "anomalyPoint": {
                    "type": "integer",
                    "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                    "minimum": 0,
                    "maximum": 3
                  },
                  "eventId": {
                    "type": "string",
                    "description": "Event id&Incident identity used to correlate the original test and review.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "testVerdict": {
                    "type": "string",
                    "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                    "enum": [
                      "confirmed",
                      "cleared",
                      "inconclusive"
                    ]
                  }
                },
                "required": [],
                "additionalProperties": false,
                "anyOf": [
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      }
                    },
                    "required": [
                      "probeNodeId"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      }
                    },
                    "required": [
                      "watchTaskId"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      }
                    },
                    "required": [
                      "executionMode",
                      "areaId",
                      "pointIds"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      },
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 60
                      }
                    },
                    "required": [
                      "executionMode",
                      "eventId"
                    ],
                    "additionalProperties": false
                  }
                ]
              },
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "priority": {
                "type": "integer",
                "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                "minimum": 0,
                "maximum": 9
              },
              "executeBefore": {
                "type": [
                  "integer",
                  "null"
                ],
                "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
              }
            },
            "required": [
              "executorNodeId",
              "kind",
              "config",
              "taskId"
            ],
            "additionalProperties": false,
            "oneOf": [
              {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "executorNodeId": {
                    "type": "string",
                    "description": "执行节点&Device or host selected to execute the created task.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "kind": {
                    "type": "string",
                    "description": "任务类型&Task type; selects the corresponding config and result contract.",
                    "const": "diagnostics"
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "taskId": {
                    "type": "string",
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "priority": {
                    "type": "integer",
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                    "minimum": 0,
                    "maximum": 9
                  },
                  "executeBefore": {
                    "type": [
                      "integer",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  }
                },
                "required": [
                  "executorNodeId",
                  "kind",
                  "config",
                  "taskId"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "executorNodeId": {
                    "type": "string",
                    "description": "执行节点&Device or host selected to execute the created task.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "kind": {
                    "type": "string",
                    "description": "任务类型&Task type; selects the corresponding config and result contract.",
                    "const": "network_diagnostics"
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      }
                    },
                    "required": [
                      "probeNodeId"
                    ],
                    "additionalProperties": false
                  },
                  "taskId": {
                    "type": "string",
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "priority": {
                    "type": "integer",
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                    "minimum": 0,
                    "maximum": 9
                  },
                  "executeBefore": {
                    "type": [
                      "integer",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  }
                },
                "required": [
                  "executorNodeId",
                  "kind",
                  "config",
                  "taskId"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "executorNodeId": {
                    "type": "string",
                    "description": "执行节点&Device or host selected to execute the created task.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "kind": {
                    "type": "string",
                    "description": "任务类型&Task type; selects the corresponding config and result contract.",
                    "const": "task_monitor"
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      }
                    },
                    "required": [
                      "watchTaskId"
                    ],
                    "additionalProperties": false
                  },
                  "taskId": {
                    "type": "string",
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "priority": {
                    "type": "integer",
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                    "minimum": 0,
                    "maximum": 9
                  },
                  "executeBefore": {
                    "type": [
                      "integer",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  }
                },
                "required": [
                  "executorNodeId",
                  "kind",
                  "config",
                  "taskId"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "executorNodeId": {
                    "type": "string",
                    "description": "执行节点&Device or host selected to execute the created task.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "kind": {
                    "type": "string",
                    "description": "任务类型&Task type; selects the corresponding config and result contract.",
                    "const": "patrol"
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      }
                    },
                    "required": [
                      "executionMode",
                      "areaId",
                      "pointIds"
                    ],
                    "additionalProperties": false
                  },
                  "taskId": {
                    "type": "string",
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "priority": {
                    "type": "integer",
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                    "minimum": 0,
                    "maximum": 9
                  },
                  "executeBefore": {
                    "type": [
                      "integer",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  }
                },
                "required": [
                  "executorNodeId",
                  "kind",
                  "config",
                  "taskId"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "description": "Business record&Fields follow the published method contract.",
                "properties": {
                  "executorNodeId": {
                    "type": "string",
                    "description": "执行节点&Device or host selected to execute the created task.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "kind": {
                    "type": "string",
                    "description": "任务类型&Task type; selects the corresponding config and result contract.",
                    "const": "anomaly_review"
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      },
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 60
                      }
                    },
                    "required": [
                      "executionMode",
                      "eventId"
                    ],
                    "additionalProperties": false
                  },
                  "taskId": {
                    "type": "string",
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "priority": {
                    "type": "integer",
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                    "minimum": 0,
                    "maximum": 9
                  },
                  "executeBefore": {
                    "type": [
                      "integer",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  }
                },
                "required": [
                  "executorNodeId",
                  "kind",
                  "config",
                  "taskId"
                ],
                "additionalProperties": false
              }
            ]
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_DeleteTaskHistory",
          "description": "删除任务历史&成功表示符合删除条件的终态历史已删除，不清除设备 NVS。",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "deleted": {
                "type": "boolean",
                "description": "Deleted&Whether eligible terminal task history has been removed; device NVS is not erased."
              },
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "maxLength": 256
              },
              "stateSeq": {
                "type": "integer",
                "description": "State seq&Monotonic state-change sequence for replay ordering.",
                "minimum": 0
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              }
            },
            "required": [],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_PauseTask",
          "description": "暂停任务&成功表示暂停意图已受理；后续状态为 PAUSED 才确认暂停。",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_ResumeTask",
          "description": "恢复任务&成功表示恢复意图已受理；后续状态为 RUNNING 才确认恢复。",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_StartTask",
          "description": "开始任务&成功表示开始意图已入队，不表示开始执行或执行完成。",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Cnr_UpdateTask",
          "description": "Update task&Only CREATED tasks; config is checked against stored kind.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              },
              "expectedRevision": {
                "type": "integer",
                "description": "预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision.",
                "minimum": 0
              },
              "config": {
                "type": "object",
                "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                "properties": {
                  "durationSeconds": {
                    "type": "integer",
                    "description": "Business value&See the method contract for meaning and constraints.",
                    "minimum": 1,
                    "maximum": 3600
                  },
                  "periodMs": {
                    "type": "integer",
                    "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                    "minimum": 200,
                    "maximum": 10000
                  },
                  "probeNodeId": {
                    "type": "string",
                    "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "watchTaskId": {
                    "type": "string",
                    "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "staleAfterSeconds": {
                    "type": "integer",
                    "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                    "minimum": 1,
                    "maximum": 3600
                  },
                  "executionMode": {
                    "type": "string",
                    "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                    "const": "esp32_test"
                  },
                  "areaId": {
                    "type": "string",
                    "description": "Area id&Logical test area identifier.",
                    "pattern": "^[A-Za-z0-9_-]{1,12}$"
                  },
                  "pointIds": {
                    "type": "array",
                    "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                    "items": {
                      "type": "string",
                      "description": "Business value&See the method contract for meaning and constraints.",
                      "pattern": "^[A-Za-z0-9_-]{1,12}$"
                    },
                    "minItems": 1,
                    "maxItems": 3,
                    "uniqueItems": true
                  },
                  "pointDurationSeconds": {
                    "type": "integer",
                    "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                    "minimum": 1,
                    "maximum": 60
                  },
                  "anomalyPoint": {
                    "type": "integer",
                    "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                    "minimum": 0,
                    "maximum": 3
                  },
                  "eventId": {
                    "type": "string",
                    "description": "Event id&Incident identity used to correlate the original test and review.",
                    "pattern": "^[A-Za-z0-9_-]{1,32}$",
                    "minLength": 1,
                    "maxLength": 32
                  },
                  "testVerdict": {
                    "type": "string",
                    "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                    "enum": [
                      "confirmed",
                      "cleared",
                      "inconclusive"
                    ]
                  }
                },
                "required": [],
                "additionalProperties": false,
                "anyOf": [
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      }
                    },
                    "required": [
                      "probeNodeId"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      }
                    },
                    "required": [
                      "watchTaskId"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      }
                    },
                    "required": [
                      "executionMode",
                      "areaId",
                      "pointIds"
                    ],
                    "additionalProperties": false
                  },
                  {
                    "type": "object",
                    "description": "Business record&Fields follow the published method contract.",
                    "properties": {
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      },
                      "durationSeconds": {
                        "type": "integer",
                        "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                        "minimum": 1,
                        "maximum": 60
                      }
                    },
                    "required": [
                      "executionMode",
                      "eventId"
                    ],
                    "additionalProperties": false
                  }
                ]
              },
              "priority": {
                "type": "integer",
                "description": "Priority&Queue priority from 0 through 9; omission uses zero.",
                "minimum": 0,
                "maximum": 9
              },
              "executeBefore": {
                "type": [
                  "integer",
                  "null"
                ],
                "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
              }
            },
            "required": [
              "taskId",
              "expectedRevision"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Et_TestIncident",
          "description": "Test incident&One-way validated ESP32 test event; no physical recognition claim.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "eventId": {
                "type": "string",
                "description": "Event id&Incident identity used to correlate the original test and review.",
                "maxLength": 256
              },
              "sourceTaskId": {
                "type": "string",
                "description": "Source task id&Task that generated this test incident.",
                "maxLength": 256
              },
              "nodeId": {
                "type": "string",
                "description": "Node id&Identity of the node described by this record.",
                "maxLength": 256
              },
              "areaId": {
                "type": "string",
                "description": "Area id&Logical test area identifier.",
                "maxLength": 256
              },
              "pointId": {
                "type": "string",
                "description": "Point id&Test point that generated the incident.",
                "maxLength": 256
              },
              "created": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Created&Creation time as Unix seconds."
              },
              "test": {
                "type": "boolean",
                "description": "Test&True for ESP32 test incidents; not evidence of real-world detection."
              },
              "executionMode": {
                "type": "string",
                "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                "maxLength": 256
              }
            },
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": null
        },
        {
          "method": "Get_Task",
          "description": "Read task&Returns last known persisted state.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              }
            },
            "required": [
              "taskId"
            ],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "task": {
                "type": "object",
                "description": "Task&Persisted task view; includes state and revision, not a physical-completion promise.",
                "properties": {
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "kind": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务类型&Task type; selects the corresponding config and result contract."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "revision": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                  },
                  "priority": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                  },
                  "executeBefore": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                  },
                  "created": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Created&Creation time as Unix seconds."
                  },
                  "updated": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Updated&Last persisted change as Unix seconds."
                  },
                  "stateSeq": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "State seq&Monotonic state-change sequence for replay ordering."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "feedbackAt": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                  },
                  "config": {
                    "type": "object",
                    "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                    "properties": {
                      "durationSeconds": {
                        "type": "integer",
                        "description": "Business value&See the method contract for meaning and constraints.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "periodMs": {
                        "type": "integer",
                        "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                        "minimum": 200,
                        "maximum": 10000
                      },
                      "probeNodeId": {
                        "type": "string",
                        "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "watchTaskId": {
                        "type": "string",
                        "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "staleAfterSeconds": {
                        "type": "integer",
                        "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                        "minimum": 1,
                        "maximum": 3600
                      },
                      "executionMode": {
                        "type": "string",
                        "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                        "const": "esp32_test"
                      },
                      "areaId": {
                        "type": "string",
                        "description": "Area id&Logical test area identifier.",
                        "pattern": "^[A-Za-z0-9_-]{1,12}$"
                      },
                      "pointIds": {
                        "type": "array",
                        "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                        "items": {
                          "type": "string",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": true
                      },
                      "pointDurationSeconds": {
                        "type": "integer",
                        "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                        "minimum": 1,
                        "maximum": 60
                      },
                      "anomalyPoint": {
                        "type": "integer",
                        "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                        "minimum": 0,
                        "maximum": 3
                      },
                      "eventId": {
                        "type": "string",
                        "description": "Event id&Incident identity used to correlate the original test and review.",
                        "pattern": "^[A-Za-z0-9_-]{1,32}$",
                        "minLength": 1,
                        "maxLength": 32
                      },
                      "testVerdict": {
                        "type": "string",
                        "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                        "enum": [
                          "confirmed",
                          "cleared",
                          "inconclusive"
                        ]
                      }
                    },
                    "required": [],
                    "additionalProperties": false,
                    "anyOf": [
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          }
                        },
                        "required": [],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "probeNodeId": {
                            "type": "string",
                            "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          }
                        },
                        "required": [
                          "probeNodeId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 3600
                          },
                          "periodMs": {
                            "type": "integer",
                            "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                            "minimum": 200,
                            "maximum": 10000
                          },
                          "watchTaskId": {
                            "type": "string",
                            "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "staleAfterSeconds": {
                            "type": "integer",
                            "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                            "minimum": 1,
                            "maximum": 3600
                          }
                        },
                        "required": [
                          "watchTaskId"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "areaId": {
                            "type": "string",
                            "description": "Area id&Logical test area identifier.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "pointIds": {
                            "type": "array",
                            "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                            "items": {
                              "type": "string",
                              "description": "Business value&See the method contract for meaning and constraints.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "uniqueItems": true
                          },
                          "pointDurationSeconds": {
                            "type": "integer",
                            "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                            "minimum": 1,
                            "maximum": 60
                          },
                          "anomalyPoint": {
                            "type": "integer",
                            "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                            "minimum": 0,
                            "maximum": 3
                          }
                        },
                        "required": [
                          "executionMode",
                          "areaId",
                          "pointIds"
                        ],
                        "additionalProperties": false
                      },
                      {
                        "type": "object",
                        "description": "Business record&Fields follow the published method contract.",
                        "properties": {
                          "executionMode": {
                            "type": "string",
                            "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                            "const": "esp32_test"
                          },
                          "eventId": {
                            "type": "string",
                            "description": "Event id&Incident identity used to correlate the original test and review.",
                            "pattern": "^[A-Za-z0-9_-]{1,32}$",
                            "minLength": 1,
                            "maxLength": 32
                          },
                          "testVerdict": {
                            "type": "string",
                            "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                            "enum": [
                              "confirmed",
                              "cleared",
                              "inconclusive"
                            ]
                          },
                          "durationSeconds": {
                            "type": "integer",
                            "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                            "minimum": 1,
                            "maximum": 60
                          }
                        },
                        "required": [
                          "executionMode",
                          "eventId"
                        ],
                        "additionalProperties": false
                      }
                    ]
                  },
                  "result": {
                    "type": "object",
                    "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                    "properties": {
                      "source": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Source&Metrics source: c6 or ugv_host."
                      },
                      "nodeId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Node id&Identity of the node described by this record."
                      },
                      "taskId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                      },
                      "target": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Target&Task executor identity, or monitored task executor in a result."
                      },
                      "state": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                      },
                      "health": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Health&Monitor health classification, distinct from task execution state."
                      },
                      "error": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Error&Known operation or execution error; null means no recorded error."
                      },
                      "mode": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                      },
                      "stage": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                      },
                      "point": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Point&Current ESP32 test point identity."
                      },
                      "eventId": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Event id&Incident identity used to correlate the original test and review."
                      },
                      "verdict": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Verdict&Reported test review conclusion, not actual recognition."
                      },
                      "samples": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Samples&Number of collected diagnostic samples."
                      },
                      "readyNodes": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                      },
                      "ok": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Ok&Successful network probe count."
                      },
                      "failed": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Failed&Failed network probe count."
                      },
                      "lastMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                      },
                      "avgMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "maxMs": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                      },
                      "ageS": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Age s&Valid feedback or snapshot age in seconds."
                      },
                      "progress": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Progress&Reported execution progress in percent."
                      },
                      "done": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Done&Completed ESP32 test point count."
                      },
                      "total": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Total&Total ESP32 test point count."
                      },
                      "rssi": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                      },
                      "rssiMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi min&Minimum sampled RSSI in dBm."
                      },
                      "rssiMax": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Rssi max&Maximum sampled RSSI in dBm."
                      },
                      "heap": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap&Current free heap in bytes."
                      },
                      "heapMin": {
                        "type": [
                          "number",
                          "null"
                        ],
                        "description": "Heap min&Minimum free heap in bytes."
                      },
                      "ready": {
                        "type": [
                          "boolean",
                          "null"
                        ],
                        "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  },
                  "lastOperation": {
                    "type": "object",
                    "description": "Last operation&Last persisted control operation and dispatch state.",
                    "properties": {
                      "commandId": {
                        "type": "string",
                        "description": "Command id&Internal task operation identity returned as business tracking information.",
                        "maxLength": 256
                      },
                      "op": {
                        "type": "string",
                        "description": "Op&Task control operation.",
                        "maxLength": 256
                      },
                      "status": {
                        "type": "string",
                        "description": "Status&Observed device state or null if no observation exists.",
                        "maxLength": 256
                      },
                      "opSeq": {
                        "type": "integer",
                        "description": "Op seq&Monotonic task operation sequence.",
                        "minimum": 0
                      }
                    },
                    "required": [],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "taskId",
                  "kind",
                  "state",
                  "revision"
                ],
                "additionalProperties": false
              },
              "stage": {
                "type": "string",
                "description": "Stage&Processing stage, including acceptance versus final application or test progress.",
                "maxLength": 256
              },
              "commandId": {
                "type": "string",
                "description": "Command id&Internal task operation identity returned as business tracking information.",
                "maxLength": 256
              }
            },
            "required": [
              "task"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_TaskEvents",
          "description": "Read events&Caller-owned durable history; incident results are ESP32 test data.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              },
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              }
            },
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "items": {
                "type": "array",
                "description": "本页记录&Current page of tasks, state events or test incidents.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "taskId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                    },
                    "state": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                    },
                    "error": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Error&Known operation or execution error; null means no recorded error."
                    },
                    "revision": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                    },
                    "priority": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                    },
                    "executeBefore": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                    },
                    "created": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Created&Creation time as Unix seconds."
                    },
                    "updated": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Updated&Last persisted change as Unix seconds."
                    },
                    "stateSeq": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "State seq&Monotonic state-change sequence for replay ordering."
                    },
                    "progress": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Progress&Reported execution progress in percent."
                    },
                    "feedbackAt": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                    },
                    "result": {
                      "type": "object",
                      "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                      "properties": {
                        "source": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Source&Metrics source: c6 or ugv_host."
                        },
                        "nodeId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Node id&Identity of the node described by this record."
                        },
                        "taskId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                        },
                        "target": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Target&Task executor identity, or monitored task executor in a result."
                        },
                        "state": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                        },
                        "health": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Health&Monitor health classification, distinct from task execution state."
                        },
                        "error": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Error&Known operation or execution error; null means no recorded error."
                        },
                        "mode": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                        },
                        "stage": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                        },
                        "point": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Point&Current ESP32 test point identity."
                        },
                        "eventId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Event id&Incident identity used to correlate the original test and review."
                        },
                        "verdict": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Verdict&Reported test review conclusion, not actual recognition."
                        },
                        "samples": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Samples&Number of collected diagnostic samples."
                        },
                        "readyNodes": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                        },
                        "ok": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Ok&Successful network probe count."
                        },
                        "failed": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Failed&Failed network probe count."
                        },
                        "lastMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                        },
                        "avgMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                        },
                        "maxMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                        },
                        "ageS": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Age s&Valid feedback or snapshot age in seconds."
                        },
                        "progress": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Progress&Reported execution progress in percent."
                        },
                        "done": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Done&Completed ESP32 test point count."
                        },
                        "total": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Total&Total ESP32 test point count."
                        },
                        "rssi": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                        },
                        "rssiMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi min&Minimum sampled RSSI in dBm."
                        },
                        "rssiMax": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi max&Maximum sampled RSSI in dBm."
                        },
                        "heap": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap&Current free heap in bytes."
                        },
                        "heapMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap min&Minimum free heap in bytes."
                        },
                        "ready": {
                          "type": [
                            "boolean",
                            "null"
                          ],
                          "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    },
                    "cursor": {
                      "type": "integer",
                      "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                      "minimum": 0,
                      "maximum": 9223372036854775807
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              },
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              },
              "more": {
                "type": "boolean",
                "description": "是否还有下一页&Whether another page is available after this cursor."
              }
            },
            "required": [
              "items",
              "cursor",
              "more"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_TaskList",
          "description": "List tasks&Returns caller-owned tasks using cursor pagination.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              }
            },
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "items": {
                "type": "array",
                "description": "本页记录&Current page of tasks, state events or test incidents.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "taskId": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                    },
                    "target": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Target&Task executor identity, or monitored task executor in a result."
                    },
                    "kind": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "任务类型&Task type; selects the corresponding config and result contract."
                    },
                    "state": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                    },
                    "error": {
                      "type": [
                        "string",
                        "null"
                      ],
                      "description": "Error&Known operation or execution error; null means no recorded error."
                    },
                    "revision": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Revision&Current task or parent policy revision; these revision domains are independent."
                    },
                    "priority": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Priority&Queue priority from 0 through 9; omission uses zero."
                    },
                    "executeBefore": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
                    },
                    "created": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Created&Creation time as Unix seconds."
                    },
                    "updated": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Updated&Last persisted change as Unix seconds."
                    },
                    "stateSeq": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "State seq&Monotonic state-change sequence for replay ordering."
                    },
                    "progress": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Progress&Reported execution progress in percent."
                    },
                    "feedbackAt": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
                    },
                    "config": {
                      "type": "object",
                      "description": "任务配置&Task configuration; validated against kind or the stored task kind when updating.",
                      "properties": {
                        "durationSeconds": {
                          "type": "integer",
                          "description": "Business value&See the method contract for meaning and constraints.",
                          "minimum": 1,
                          "maximum": 3600
                        },
                        "periodMs": {
                          "type": "integer",
                          "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                          "minimum": 200,
                          "maximum": 10000
                        },
                        "probeNodeId": {
                          "type": "string",
                          "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                          "pattern": "^[A-Za-z0-9_-]{1,32}$",
                          "minLength": 1,
                          "maxLength": 32
                        },
                        "watchTaskId": {
                          "type": "string",
                          "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                          "pattern": "^[A-Za-z0-9_-]{1,32}$",
                          "minLength": 1,
                          "maxLength": 32
                        },
                        "staleAfterSeconds": {
                          "type": "integer",
                          "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                          "minimum": 1,
                          "maximum": 3600
                        },
                        "executionMode": {
                          "type": "string",
                          "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                          "const": "esp32_test"
                        },
                        "areaId": {
                          "type": "string",
                          "description": "Area id&Logical test area identifier.",
                          "pattern": "^[A-Za-z0-9_-]{1,12}$"
                        },
                        "pointIds": {
                          "type": "array",
                          "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                          "items": {
                            "type": "string",
                            "description": "Business value&See the method contract for meaning and constraints.",
                            "pattern": "^[A-Za-z0-9_-]{1,12}$"
                          },
                          "minItems": 1,
                          "maxItems": 3,
                          "uniqueItems": true
                        },
                        "pointDurationSeconds": {
                          "type": "integer",
                          "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                          "minimum": 1,
                          "maximum": 60
                        },
                        "anomalyPoint": {
                          "type": "integer",
                          "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                          "minimum": 0,
                          "maximum": 3
                        },
                        "eventId": {
                          "type": "string",
                          "description": "Event id&Incident identity used to correlate the original test and review.",
                          "pattern": "^[A-Za-z0-9_-]{1,32}$",
                          "minLength": 1,
                          "maxLength": 32
                        },
                        "testVerdict": {
                          "type": "string",
                          "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                          "enum": [
                            "confirmed",
                            "cleared",
                            "inconclusive"
                          ]
                        }
                      },
                      "required": [],
                      "additionalProperties": false,
                      "anyOf": [
                        {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "durationSeconds": {
                              "type": "integer",
                              "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                              "minimum": 1,
                              "maximum": 3600
                            },
                            "periodMs": {
                              "type": "integer",
                              "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                              "minimum": 200,
                              "maximum": 10000
                            }
                          },
                          "required": [],
                          "additionalProperties": false
                        },
                        {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "durationSeconds": {
                              "type": "integer",
                              "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                              "minimum": 1,
                              "maximum": 3600
                            },
                            "periodMs": {
                              "type": "integer",
                              "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                              "minimum": 200,
                              "maximum": 10000
                            },
                            "probeNodeId": {
                              "type": "string",
                              "description": "被检查节点&Authorized remote node to probe; cannot be the local root host.",
                              "pattern": "^[A-Za-z0-9_-]{1,32}$",
                              "minLength": 1,
                              "maxLength": 32
                            }
                          },
                          "required": [
                            "probeNodeId"
                          ],
                          "additionalProperties": false
                        },
                        {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "durationSeconds": {
                              "type": "integer",
                              "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                              "minimum": 1,
                              "maximum": 3600
                            },
                            "periodMs": {
                              "type": "integer",
                              "description": "采样周期&Sampling period in milliseconds; omission uses 1000.",
                              "minimum": 200,
                              "maximum": 10000
                            },
                            "watchTaskId": {
                              "type": "string",
                              "description": "被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited.",
                              "pattern": "^[A-Za-z0-9_-]{1,32}$",
                              "minLength": 1,
                              "maxLength": 32
                            },
                            "staleAfterSeconds": {
                              "type": "integer",
                              "description": "Stale after seconds&Feedback freshness threshold in seconds; omission uses 10.",
                              "minimum": 1,
                              "maximum": 3600
                            }
                          },
                          "required": [
                            "watchTaskId"
                          ],
                          "additionalProperties": false
                        },
                        {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "executionMode": {
                              "type": "string",
                              "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                              "const": "esp32_test"
                            },
                            "areaId": {
                              "type": "string",
                              "description": "Area id&Logical test area identifier.",
                              "pattern": "^[A-Za-z0-9_-]{1,12}$"
                            },
                            "pointIds": {
                              "type": "array",
                              "description": "Point ids&Ordered distinct test point identifiers; no physical flight coordinates.",
                              "items": {
                                "type": "string",
                                "description": "Business value&See the method contract for meaning and constraints.",
                                "pattern": "^[A-Za-z0-9_-]{1,12}$"
                              },
                              "minItems": 1,
                              "maxItems": 3,
                              "uniqueItems": true
                            },
                            "pointDurationSeconds": {
                              "type": "integer",
                              "description": "Point duration seconds&Time spent on each test point in seconds; omission uses 3.",
                              "minimum": 1,
                              "maximum": 60
                            },
                            "anomalyPoint": {
                              "type": "integer",
                              "description": "Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero.",
                              "minimum": 0,
                              "maximum": 3
                            }
                          },
                          "required": [
                            "executionMode",
                            "areaId",
                            "pointIds"
                          ],
                          "additionalProperties": false
                        },
                        {
                          "type": "object",
                          "description": "Business record&Fields follow the published method contract.",
                          "properties": {
                            "executionMode": {
                              "type": "string",
                              "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                              "const": "esp32_test"
                            },
                            "eventId": {
                              "type": "string",
                              "description": "Event id&Incident identity used to correlate the original test and review.",
                              "pattern": "^[A-Za-z0-9_-]{1,32}$",
                              "minLength": 1,
                              "maxLength": 32
                            },
                            "testVerdict": {
                              "type": "string",
                              "description": "Test verdict&Preset test review outcome; omission uses inconclusive.",
                              "enum": [
                                "confirmed",
                                "cleared",
                                "inconclusive"
                              ]
                            },
                            "durationSeconds": {
                              "type": "integer",
                              "description": "持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.",
                              "minimum": 1,
                              "maximum": 60
                            }
                          },
                          "required": [
                            "executionMode",
                            "eventId"
                          ],
                          "additionalProperties": false
                        }
                      ]
                    },
                    "result": {
                      "type": "object",
                      "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                      "properties": {
                        "source": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Source&Metrics source: c6 or ugv_host."
                        },
                        "nodeId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Node id&Identity of the node described by this record."
                        },
                        "taskId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                        },
                        "target": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Target&Task executor identity, or monitored task executor in a result."
                        },
                        "state": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                        },
                        "health": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Health&Monitor health classification, distinct from task execution state."
                        },
                        "error": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Error&Known operation or execution error; null means no recorded error."
                        },
                        "mode": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                        },
                        "stage": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                        },
                        "point": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Point&Current ESP32 test point identity."
                        },
                        "eventId": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Event id&Incident identity used to correlate the original test and review."
                        },
                        "verdict": {
                          "type": [
                            "string",
                            "null"
                          ],
                          "description": "Verdict&Reported test review conclusion, not actual recognition."
                        },
                        "samples": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Samples&Number of collected diagnostic samples."
                        },
                        "readyNodes": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                        },
                        "ok": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Ok&Successful network probe count."
                        },
                        "failed": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Failed&Failed network probe count."
                        },
                        "lastMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                        },
                        "avgMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                        },
                        "maxMs": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                        },
                        "ageS": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Age s&Valid feedback or snapshot age in seconds."
                        },
                        "progress": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Progress&Reported execution progress in percent."
                        },
                        "done": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Done&Completed ESP32 test point count."
                        },
                        "total": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Total&Total ESP32 test point count."
                        },
                        "rssi": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                        },
                        "rssiMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi min&Minimum sampled RSSI in dBm."
                        },
                        "rssiMax": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Rssi max&Maximum sampled RSSI in dBm."
                        },
                        "heap": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap&Current free heap in bytes."
                        },
                        "heapMin": {
                          "type": [
                            "number",
                            "null"
                          ],
                          "description": "Heap min&Minimum free heap in bytes."
                        },
                        "ready": {
                          "type": [
                            "boolean",
                            "null"
                          ],
                          "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    },
                    "lastOperation": {
                      "type": "object",
                      "description": "Last operation&Last persisted control operation and dispatch state.",
                      "properties": {
                        "commandId": {
                          "type": "string",
                          "description": "Command id&Internal task operation identity returned as business tracking information.",
                          "maxLength": 256
                        },
                        "op": {
                          "type": "string",
                          "description": "Op&Task control operation.",
                          "maxLength": 256
                        },
                        "status": {
                          "type": "string",
                          "description": "Status&Observed device state or null if no observation exists.",
                          "maxLength": 256
                        },
                        "opSeq": {
                          "type": "integer",
                          "description": "Op seq&Monotonic task operation sequence.",
                          "minimum": 0
                        }
                      },
                      "required": [],
                      "additionalProperties": false
                    }
                  },
                  "required": [
                    "taskId",
                    "kind",
                    "state",
                    "revision"
                  ],
                  "additionalProperties": false
                }
              },
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              },
              "more": {
                "type": "boolean",
                "description": "是否还有下一页&Whether another page is available after this cursor."
              }
            },
            "required": [
              "items",
              "cursor",
              "more"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Get_TestIncidents",
          "description": "Read events&Caller-owned durable history; incident results are ESP32 test data.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              },
              "taskId": {
                "type": "string",
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions.",
                "pattern": "^[A-Za-z0-9_-]{1,32}$",
                "minLength": 1,
                "maxLength": 32
              }
            },
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "items": {
                "type": "array",
                "description": "本页记录&Current page of tasks, state events or test incidents.",
                "items": {
                  "type": "object",
                  "description": "Business record&Fields follow the published method contract.",
                  "properties": {
                    "eventId": {
                      "type": "string",
                      "description": "Event id&Incident identity used to correlate the original test and review.",
                      "maxLength": 256
                    },
                    "sourceTaskId": {
                      "type": "string",
                      "description": "Source task id&Task that generated this test incident.",
                      "maxLength": 256
                    },
                    "nodeId": {
                      "type": "string",
                      "description": "Node id&Identity of the node described by this record.",
                      "maxLength": 256
                    },
                    "areaId": {
                      "type": "string",
                      "description": "Area id&Logical test area identifier.",
                      "maxLength": 256
                    },
                    "pointId": {
                      "type": "string",
                      "description": "Point id&Test point that generated the incident.",
                      "maxLength": 256
                    },
                    "created": {
                      "type": [
                        "number",
                        "null"
                      ],
                      "description": "Created&Creation time as Unix seconds."
                    },
                    "test": {
                      "type": "boolean",
                      "description": "Test&True for ESP32 test incidents; not evidence of real-world detection."
                    },
                    "executionMode": {
                      "type": "string",
                      "description": "Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.",
                      "maxLength": 256
                    }
                  },
                  "required": [],
                  "additionalProperties": false
                }
              },
              "cursor": {
                "type": "integer",
                "description": "查询游标&Durable pagination or replay cursor; zero starts from the beginning.",
                "minimum": 0,
                "maximum": 9223372036854775807
              },
              "more": {
                "type": "boolean",
                "description": "是否还有下一页&Whether another page is available after this cursor."
              }
            },
            "required": [
              "items",
              "cursor",
              "more"
            ],
            "additionalProperties": false
          }
        },
        {
          "method": "Ntf_TaskChanged",
          "description": "Task change&One-way persisted state notification, not a control request.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "taskId": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
              },
              "state": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
              },
              "error": {
                "type": [
                  "string",
                  "null"
                ],
                "description": "Error&Known operation or execution error; null means no recorded error."
              },
              "revision": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Revision&Current task or parent policy revision; these revision domains are independent."
              },
              "priority": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Priority&Queue priority from 0 through 9; omission uses zero."
              },
              "executeBefore": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Execute before&Latest allowed execution start as Unix seconds; null means no such deadline."
              },
              "created": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Created&Creation time as Unix seconds."
              },
              "updated": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Updated&Last persisted change as Unix seconds."
              },
              "stateSeq": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "State seq&Monotonic state-change sequence for replay ordering."
              },
              "progress": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Progress&Reported execution progress in percent."
              },
              "feedbackAt": {
                "type": [
                  "number",
                  "null"
                ],
                "description": "Feedback at&Host receive time of valid executor feedback as Unix seconds."
              },
              "result": {
                "type": "object",
                "description": "业务结果&Recorded metrics or ESP32 workflow result; absent until reported.",
                "properties": {
                  "source": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Source&Metrics source: c6 or ugv_host."
                  },
                  "nodeId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Node id&Identity of the node described by this record."
                  },
                  "taskId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions."
                  },
                  "target": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Target&Task executor identity, or monitored task executor in a result."
                  },
                  "state": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "当前状态&Known task or policy state; accepted does not mean physical execution completed."
                  },
                  "health": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Health&Monitor health classification, distinct from task execution state."
                  },
                  "error": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Error&Known operation or execution error; null means no recorded error."
                  },
                  "mode": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode."
                  },
                  "stage": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Stage&Processing stage, including acceptance versus final application or test progress."
                  },
                  "point": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Point&Current ESP32 test point identity."
                  },
                  "eventId": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Event id&Incident identity used to correlate the original test and review."
                  },
                  "verdict": {
                    "type": [
                      "string",
                      "null"
                    ],
                    "description": "Verdict&Reported test review conclusion, not actual recognition."
                  },
                  "samples": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Samples&Number of collected diagnostic samples."
                  },
                  "readyNodes": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Ready nodes&Number of ready nodes observed by host diagnostics."
                  },
                  "ok": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Ok&Successful network probe count."
                  },
                  "failed": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Failed&Failed network probe count."
                  },
                  "lastMs": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement."
                  },
                  "avgMs": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded."
                  },
                  "maxMs": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded."
                  },
                  "ageS": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Age s&Valid feedback or snapshot age in seconds."
                  },
                  "progress": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Progress&Reported execution progress in percent."
                  },
                  "done": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Done&Completed ESP32 test point count."
                  },
                  "total": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Total&Total ESP32 test point count."
                  },
                  "rssi": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Rssi&Reported Wi-Fi received signal strength in dBm."
                  },
                  "rssiMin": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Rssi min&Minimum sampled RSSI in dBm."
                  },
                  "rssiMax": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Rssi max&Maximum sampled RSSI in dBm."
                  },
                  "heap": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Heap&Current free heap in bytes."
                  },
                  "heapMin": {
                    "type": [
                      "number",
                      "null"
                    ],
                    "description": "Heap min&Minimum free heap in bytes."
                  },
                  "ready": {
                    "type": [
                      "boolean",
                      "null"
                    ],
                    "description": "Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet."
                  }
                },
                "required": [],
                "additionalProperties": false
              }
            },
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": null
        }
      ]
    }
  ]
}
```

## A.2 业务 key 逐项说明

路径表示实际业务数据，不包含 `properties` 等 Schema 关键字。字段说明保留实际发布的“用户描述&详细描述”。
必填性在所属对象内生效，子字段必填不等于父字段必填。分支行只在对应 kind 或 Schema 分支生效，公共约束仍同时适用。
oneOf 要求恰好匹配一个分支；anyOf 要求至少匹配一个分支。Schema 的 default 不自动补值，运行时默认值以字段说明为准。

### Mesh_Admission

#### Mesh_Admission.Cnr_SetTrustStatus

Manage trust&Success persists admission; broker ACL still requires controlled reload.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | trustStatus | string | 是（所属对象出现时） | {"enum": ["pending", "trusted", "revoked"]} | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | trustStatus | string | 否 | {"maxLength": 256} | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | admissionRevision | integer | 否 | {"minimum": 0} | Admission revision&Admission decision revision, distinct from task or parent policy revision. |
| 公共定义 | brokerAclApplied | boolean | 否 | — | Broker acl applied&Whether broker enforcement has been applied; current adapter returns false. |
| 公共定义 | brokerAclReloadRequired | boolean | 否 | — | Broker acl reload required&Whether the generated pending broker ACL still needs controlled loading. |

### Mesh_Node

#### Mesh_Node.Cnr_Echo

Echo text&Success means the device returned the input text.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | text | string | 是（所属对象出现时） | {"maxLength": 256} | 回显文本&Text sent to or returned by the diagnostic echo operation. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | text | string | 是（所属对象出现时） | {"maxLength": 256} | 回显文本&Text sent to or returned by the diagnostic echo operation. |

#### Mesh_Node.Cnr_Ping

Probe device&Success means a matching application acknowledgement.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | acknowledged | boolean | 是（所属对象出现时） | {"const": true} | Acknowledged&True only after a matching successful application ACK. |

#### Mesh_Node.Get_NodeList

List nodes&Returns observed readiness and radio snapshots.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | nodes | array | 是（所属对象出现时） | — | 节点清单&Registered or observed nodes; historical entries do not prove current connectivity. |
| 公共定义 | nodes[].nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | nodes[].role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].rootId | ['string', 'null'] | 否 | — | Root id&Managing root node identity. |
| 公共定义 | nodes[].trustStatus | ['string', 'null'] | 否 | — | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | nodes[].ready | boolean | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | nodes[].enabled | boolean | 否 | — | Enabled&Whether the administrator enabled the inventory entry. |
| 公共定义 | nodes[].admissionRevision | integer | 否 | {"minimum": 0} | Admission revision&Admission decision revision, distinct from task or parent policy revision. |
| 公共定义 | nodes[].online | ['boolean', 'null'] | 否 | — | Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee. |
| 公共定义 | nodes[].statusAgeS | ['number', 'null'] | 否 | — | Status age s&Telemetry age in seconds, or null if unreported. |
| 公共定义 | nodes[].statusCurrentBoot | boolean | 否 | — | Status current boot&Whether telemetry belongs to the currently observed boot. |
| 公共定义 | nodes[].operations | array | 否 | — | Operations&Announced supported operations. |
| 公共定义 | nodes[].taskTypes | array | 否 | — | Task types&Announced supported task types. |
| 公共定义 | nodes[].status | ['object', 'null'] | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].status.networkStatus | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.networkStatus.status | object | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].status.networkStatus.status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].status.networkStatus.status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].status.networkStatus.status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].status.networkStatus.status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].status.networkStatus.status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].status.networkStatus.status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].status.networkStatus.status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].status.networkStatus.status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].status.networkStatus.status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].status.networkStatus.status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].status.networkStatus.status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].status.networkStatus.status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].status.networkStatus.status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].status.networkStatus.status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].status.networkStatus.status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].status.networkStatus.status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].status.networkStatus.status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].status.networkStatus.status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].status.networkStatus.status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].status.networkStatus.status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].status.networkStatus.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | nodes[].status.networkStatus.fresh | boolean | 否 | — | Fresh&Whether the root USB network snapshot is within its freshness window. |
| 公共定义 | nodes[].parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].parentPolicy.state | string | 否 | {"maxLength": 256} | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | nodes[].parentPolicy.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | nodes[].parentPolicy.actualBssid | ['string', 'null'] | 否 | — | Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy. |

#### Mesh_Node.Get_RegisteredNodes

Registration history&Does not establish live connectivity.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | nodes | array | 是（所属对象出现时） | — | 节点清单&Registered or observed nodes; historical entries do not prove current connectivity. |
| 公共定义 | nodes[].nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | nodes[].rootId | string | 否 | {"maxLength": 256} | Root id&Managing root node identity. |
| 公共定义 | nodes[].registered | boolean | 否 | — | Registered&Whether this historical catalog entry is still in the administrator inventory. |
| 公共定义 | nodes[].observedAt | ['number', 'null'] | 否 | — | Observed at&Host observation time as Unix seconds or null if unknown. |
| 公共定义 | nodes[].registration | object | 否 | — | Registration&Administrator registration snapshot; observations cannot grant trust. |
| 公共定义 | nodes[].registration.nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | nodes[].registration.rootId | string | 否 | {"maxLength": 256} | Root id&Managing root node identity. |
| 公共定义 | nodes[].registration.role | string | 否 | {"maxLength": 256} | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].registration.enabled | boolean | 否 | — | Enabled&Whether the administrator enabled the inventory entry. |
| 公共定义 | nodes[].registration.apSubnet | ['number', 'null'] | 否 | — | Ap subnet&Reserved 192.168.N.0/24 AP subnet index; null for STA-only leaves. |
| 公共定义 | nodes[].registration.trustStatus | string | 否 | {"maxLength": 256} | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | nodes[].registration.admissionRevision | integer | 否 | {"minimum": 0} | Admission revision&Admission decision revision, distinct from task or parent policy revision. |
| 公共定义 | nodes[].lastObservation | ['object', 'null'] | 否 | — | Last observation&Last stored node snapshot or null when none has been recorded. |
| 公共定义 | nodes[].lastObservation.nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | nodes[].lastObservation.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].lastObservation.rootId | ['string', 'null'] | 否 | — | Root id&Managing root node identity. |
| 公共定义 | nodes[].lastObservation.trustStatus | ['string', 'null'] | 否 | — | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | nodes[].lastObservation.ready | boolean | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | nodes[].lastObservation.enabled | boolean | 否 | — | Enabled&Whether the administrator enabled the inventory entry. |
| 公共定义 | nodes[].lastObservation.admissionRevision | integer | 否 | {"minimum": 0} | Admission revision&Admission decision revision, distinct from task or parent policy revision. |
| 公共定义 | nodes[].lastObservation.online | ['boolean', 'null'] | 否 | — | Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee. |
| 公共定义 | nodes[].lastObservation.statusAgeS | ['number', 'null'] | 否 | — | Status age s&Telemetry age in seconds, or null if unreported. |
| 公共定义 | nodes[].lastObservation.statusCurrentBoot | boolean | 否 | — | Status current boot&Whether telemetry belongs to the currently observed boot. |
| 公共定义 | nodes[].lastObservation.operations | array | 否 | — | Operations&Announced supported operations. |
| 公共定义 | nodes[].lastObservation.taskTypes | array | 否 | — | Task types&Announced supported task types. |
| 公共定义 | nodes[].lastObservation.status | ['object', 'null'] | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].lastObservation.status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].lastObservation.status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].lastObservation.status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].lastObservation.status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].lastObservation.status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].lastObservation.status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].lastObservation.status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].lastObservation.status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].lastObservation.status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].lastObservation.status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].lastObservation.status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].lastObservation.status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].lastObservation.status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].lastObservation.status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].lastObservation.status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].lastObservation.status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].lastObservation.status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].lastObservation.status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].lastObservation.status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].lastObservation.status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].lastObservation.status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].lastObservation.status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].lastObservation.status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].lastObservation.status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].lastObservation.status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].lastObservation.status.networkStatus | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status | object | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | nodes[].lastObservation.status.networkStatus.fresh | boolean | 否 | — | Fresh&Whether the root USB network snapshot is within its freshness window. |
| 公共定义 | nodes[].lastObservation.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].lastObservation.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].lastObservation.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].lastObservation.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].lastObservation.parentPolicy.state | string | 否 | {"maxLength": 256} | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | nodes[].lastObservation.parentPolicy.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | nodes[].lastObservation.parentPolicy.actualBssid | ['string', 'null'] | 否 | — | Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy. |

#### Mesh_Node.Get_ServiceInstances

List instances&Availability is separate from method discovery.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | instances | array | 是（所属对象出现时） | — | 服务实例&Runtime capability instances and their availability, separate from method definitions. |
| 公共定义 | instances[].serviceId | ['string', 'null'] | 否 | — | Service id&Legacy runtime instance identifier, not a stable MCI service name. |
| 公共定义 | instances[].nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | instances[].agentType | ['string', 'null'] | 否 | — | Agent type&Execution agent role. |
| 公共定义 | instances[].serviceType | ['string', 'null'] | 否 | — | Service type&Legacy instance task type. |
| 公共定义 | instances[].availability | ['string', 'null'] | 否 | — | Availability&Instance availability: available, busy or unavailable. |
| 公共定义 | instances[].taskStatus | ['string', 'null'] | 否 | — | Task status&Last known instance execution state. |
| 公共定义 | instances[].taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | instances[].bootId | ['string', 'null'] | 否 | — | Boot id&Executor boot identity. |
| 公共定义 | instances[].executionMode | ['string', 'null'] | 否 | — | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | instances[].reason | ['string', 'null'] | 否 | — | Reason&Instance unavailability reason, or null when none. |
| 公共定义 | instances[].capabilities | array | 否 | — | Capabilities&Announced instance capability labels. |
| 公共定义 | instances[].operations | array | 否 | — | Operations&Announced supported operations. |
| 公共定义 | instances[].announced | boolean | 否 | — | Announced&Whether the required runtime capability has been announced. |

#### Mesh_Node.Get_Status

Read device status&Requires a ready authorized MQTT device.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | networkStatus | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | networkStatus.status | object | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | networkStatus.status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | networkStatus.status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | networkStatus.status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | networkStatus.status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | networkStatus.status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | networkStatus.status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | networkStatus.status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | networkStatus.status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | networkStatus.status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | networkStatus.status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | networkStatus.status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | networkStatus.status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | networkStatus.status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | networkStatus.status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | networkStatus.status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | networkStatus.status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | networkStatus.status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | networkStatus.status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | networkStatus.status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | networkStatus.status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | networkStatus.status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | networkStatus.status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | networkStatus.status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | networkStatus.status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | networkStatus.status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | networkStatus.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | networkStatus.fresh | boolean | 否 | — | Fresh&Whether the root USB network snapshot is within its freshness window. |

#### Mesh_Node.Ntf_NodeSnapshot

Node snapshot&One-way periodic observation; not durable history.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | nodes | array | 是（所属对象出现时） | — | 节点清单&Registered or observed nodes; historical entries do not prove current connectivity. |
| 公共定义 | nodes[].nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | nodes[].role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].rootId | ['string', 'null'] | 否 | — | Root id&Managing root node identity. |
| 公共定义 | nodes[].trustStatus | ['string', 'null'] | 否 | — | 信任状态&pending, trusted or revoked admission decision. |
| 公共定义 | nodes[].ready | boolean | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | nodes[].enabled | boolean | 否 | — | Enabled&Whether the administrator enabled the inventory entry. |
| 公共定义 | nodes[].admissionRevision | integer | 否 | {"minimum": 0} | Admission revision&Admission decision revision, distinct from task or parent policy revision. |
| 公共定义 | nodes[].online | ['boolean', 'null'] | 否 | — | Online&Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee. |
| 公共定义 | nodes[].statusAgeS | ['number', 'null'] | 否 | — | Status age s&Telemetry age in seconds, or null if unreported. |
| 公共定义 | nodes[].statusCurrentBoot | boolean | 否 | — | Status current boot&Whether telemetry belongs to the currently observed boot. |
| 公共定义 | nodes[].operations | array | 否 | — | Operations&Announced supported operations. |
| 公共定义 | nodes[].taskTypes | array | 否 | — | Task types&Announced supported task types. |
| 公共定义 | nodes[].status | ['object', 'null'] | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].status.networkStatus | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.networkStatus.status | object | 否 | — | Status&Observed device state or null if no observation exists. |
| 公共定义 | nodes[].status.networkStatus.status.role | ['string', 'null'] | 否 | — | Role&Configured device role in the four-level mesh. |
| 公共定义 | nodes[].status.networkStatus.status.topology | ['string', 'null'] | 否 | — | Topology&Configured Mesh topology. |
| 公共定义 | nodes[].status.networkStatus.status.staIp | ['string', 'null'] | 否 | — | Sta ip&Observed station IPv4 address. |
| 公共定义 | nodes[].status.networkStatus.status.apIp | ['string', 'null'] | 否 | — | Ap ip&Observed AP IPv4 address; absent for STA-only leaves. |
| 公共定义 | nodes[].status.networkStatus.status.gateway | ['string', 'null'] | 否 | — | Gateway&Observed station default gateway IPv4 address. |
| 公共定义 | nodes[].status.networkStatus.status.netmask | ['string', 'null'] | 否 | — | Netmask&Observed IPv4 netmask. |
| 公共定义 | nodes[].status.networkStatus.status.staMac | ['string', 'null'] | 否 | — | Sta mac&Station MAC address. |
| 公共定义 | nodes[].status.networkStatus.status.apMac | ['string', 'null'] | 否 | — | Ap mac&AP MAC address; absent when AP is disabled. |
| 公共定义 | nodes[].status.networkStatus.status.apSsid | ['string', 'null'] | 否 | — | Ap ssid&Advertised AP SSID. |
| 公共定义 | nodes[].status.networkStatus.status.parentBssid | ['string', 'null'] | 否 | — | Parent bssid&Observed parent AP MAC, not an inferred parent identity. |
| 公共定义 | nodes[].status.networkStatus.status.executionHost | ['string', 'null'] | 否 | — | Execution host&local identifies the host task service rather than a physical radio. |
| 公共定义 | nodes[].status.networkStatus.status.level | ['number', 'null'] | 否 | — | Level&Observed Mesh level. |
| 公共定义 | nodes[].status.networkStatus.status.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | nodes[].status.networkStatus.status.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | nodes[].status.networkStatus.status.uptimeMs | ['number', 'null'] | 否 | — | Uptime ms&Device monotonic uptime in milliseconds; not UTC. |
| 公共定义 | nodes[].status.networkStatus.status.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | nodes[].status.networkStatus.status.channel | ['number', 'null'] | 否 | — | Channel&Wi-Fi channel number. |
| 公共定义 | nodes[].status.networkStatus.status.associatedChildren | ['number', 'null'] | 否 | — | Associated children&Associated AP client count; absent for STA-only leaves. |
| 公共定义 | nodes[].status.networkStatus.status.apEnabled | boolean | 否 | — | Ap enabled&Whether this device actually has AP mode enabled. |
| 公共定义 | nodes[].status.networkStatus.status.parentConnected | boolean | 否 | — | Parent connected&Whether the device reports association to an upstream AP. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].status.networkStatus.status.parentPolicy.stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | nodes[].status.networkStatus.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | nodes[].status.networkStatus.fresh | boolean | 否 | — | Fresh&Whether the root USB network snapshot is within its freshness window. |
| 公共定义 | nodes[].parentPolicy | object | 否 | — | Business record&Fields follow the published method contract. |
| 公共定义 | nodes[].parentPolicy.mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | nodes[].parentPolicy.parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | nodes[].parentPolicy.revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | nodes[].parentPolicy.state | string | 否 | {"maxLength": 256} | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | nodes[].parentPolicy.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | nodes[].parentPolicy.actualBssid | ['string', 'null'] | 否 | — | Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy. |
| 公共定义 | brokerConnected | boolean | 是（所属对象出现时） | — | Broker connected&Whether the local host is connected to Mosquitto. |

**成功输出业务结果**

`outputSchema: null`：单向消息没有业务响应，不应作为请求—响应方法调用。

### Mesh_Parent

#### Mesh_Parent.Cnr_SetPolicy

Set parent policy&Accepted is not applied; fresh matching telemetry confirms application.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | mode | string | 是（所属对象出现时） | {"enum": ["auto", "prefer", "fixed"]} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | parentNodeId | ['string', 'null'] | 是（所属对象出现时） | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | state | string | 否 | {"maxLength": 256} | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | actualBssid | ['string', 'null'] | 否 | — | Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy. |

#### Mesh_Parent.Get_Policy

Read parent policy&Returns saved intent and available observation.

**输入业务参数或发布载荷**

空对象 `{}`，没有业务字段，禁止额外字段。

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | mode | string | 否 | {"maxLength": 256} | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | parentNodeId | ['string', 'null'] | 否 | — | 指定父节点&Desired parent UAV identity; null for automatic selection. |
| 公共定义 | revision | integer | 否 | {"minimum": 0} | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | state | string | 否 | {"maxLength": 256} | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | actualBssid | ['string', 'null'] | 否 | — | Actual bssid&Last observed upstream AP MAC; does not alone confirm the requested policy. |

### Mesh_Task

#### Mesh_Task.Cnr_CancelTask

取消任务&成功表示取消意图已受理；应查询并确认最终任务状态。

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Cnr_CreateTask

Create task&Persists CREATED; does not start execution.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| 公共定义 | kind | string | 是（所属对象出现时） | {"enum": ["diagnostics", "network_diagnostics", "task_monitor", "patrol", "anomaly_review"]} | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| kind=diagnostics | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| kind=diagnostics | kind | string | 是（所属对象出现时） | {"const": "diagnostics"} | 任务类型&Task type; selects the corresponding config and result contract. |
| kind=diagnostics | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| kind=diagnostics | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| kind=diagnostics | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| kind=diagnostics | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| kind=diagnostics | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| kind=diagnostics | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| kind=network_diagnostics | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| kind=network_diagnostics | kind | string | 是（所属对象出现时） | {"const": "network_diagnostics"} | 任务类型&Task type; selects the corresponding config and result contract. |
| kind=network_diagnostics | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| kind=network_diagnostics | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| kind=network_diagnostics | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| kind=network_diagnostics | config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| kind=network_diagnostics | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| kind=network_diagnostics | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| kind=network_diagnostics | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| kind=task_monitor | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| kind=task_monitor | kind | string | 是（所属对象出现时） | {"const": "task_monitor"} | 任务类型&Task type; selects the corresponding config and result contract. |
| kind=task_monitor | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| kind=task_monitor | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| kind=task_monitor | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| kind=task_monitor | config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| kind=task_monitor | config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| kind=task_monitor | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| kind=task_monitor | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| kind=task_monitor | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| kind=patrol | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| kind=patrol | kind | string | 是（所属对象出现时） | {"const": "patrol"} | 任务类型&Task type; selects the corresponding config and result contract. |
| kind=patrol | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| kind=patrol | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| kind=patrol | config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| kind=patrol | config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| kind=patrol | config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| kind=patrol | config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| kind=patrol | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| kind=patrol | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| kind=patrol | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| kind=anomaly_review | executorNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 执行节点&Device or host selected to execute the created task. |
| kind=anomaly_review | kind | string | 是（所属对象出现时） | {"const": "anomaly_review"} | 任务类型&Task type; selects the corresponding config and result contract. |
| kind=anomaly_review | config | object | 是（所属对象出现时） | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| kind=anomaly_review | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| kind=anomaly_review | config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| kind=anomaly_review | config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| kind=anomaly_review | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| kind=anomaly_review | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| kind=anomaly_review | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| kind=anomaly_review | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Cnr_DeleteTaskHistory

删除任务历史&成功表示符合删除条件的终态历史已删除，不清除设备 NVS。

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | deleted | boolean | 否 | — | Deleted&Whether eligible terminal task history has been removed; device NVS is not erased. |
| 公共定义 | taskId | string | 否 | {"maxLength": 256} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | stateSeq | integer | 否 | {"minimum": 0} | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |

#### Mesh_Task.Cnr_PauseTask

暂停任务&成功表示暂停意图已受理；后续状态为 PAUSED 才确认暂停。

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Cnr_ResumeTask

恢复任务&成功表示恢复意图已受理；后续状态为 RUNNING 才确认恢复。

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Cnr_StartTask

开始任务&成功表示开始意图已入队，不表示开始执行或执行完成。

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Cnr_UpdateTask

Update task&Only CREATED tasks; config is checked against stored kind.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | expectedRevision | integer | 是（所属对象出现时） | {"minimum": 0} | 预期版本&Optimistic concurrency precondition; must match the current task, admission or policy revision. |
| 公共定义 | config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | priority | integer | 否 | {"minimum": 0, "maximum": 9} | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | executeBefore | ['integer', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Et_TestIncident

Test incident&One-way validated ESP32 test event; no physical recognition claim.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | eventId | string | 否 | {"maxLength": 256} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | sourceTaskId | string | 否 | {"maxLength": 256} | Source task id&Task that generated this test incident. |
| 公共定义 | nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | areaId | string | 否 | {"maxLength": 256} | Area id&Logical test area identifier. |
| 公共定义 | pointId | string | 否 | {"maxLength": 256} | Point id&Test point that generated the incident. |
| 公共定义 | created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | test | boolean | 否 | — | Test&True for ESP32 test incidents; not evidence of real-world detection. |
| 公共定义 | executionMode | string | 否 | {"maxLength": 256} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |

**成功输出业务结果**

`outputSchema: null`：单向消息没有业务响应，不应作为请求—响应方法调用。

#### Mesh_Task.Get_Task

Read task&Returns last known persisted state.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | task | object | 是（所属对象出现时） | — | Task&Persisted task view; includes state and revision, not a physical-completion promise. |
| 公共定义 | task.taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | task.state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | task.priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | task.executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | task.created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | task.updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | task.stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | task.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | task.config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | task.config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | task.config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | task.config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | task.config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | task.config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | task.config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | task.config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | task.config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | task.config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | task.config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | task.config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | task.config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | task.config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | task.config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | task.config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | task.config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | task.config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | task.config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | task.result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | task.result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | task.result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | task.result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | task.result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | task.result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | task.result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | task.result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | task.result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | task.result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | task.result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | task.result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | task.result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | task.result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | task.result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | task.result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | task.result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | task.result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | task.result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | task.result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | task.result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | task.result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | task.result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | task.result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | task.result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | task.result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | task.result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | task.result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | task.result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | task.lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | task.lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | task.lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | task.lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | task.lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | stage | string | 否 | {"maxLength": 256} | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |

#### Mesh_Task.Get_TaskEvents

Read events&Caller-owned durable history; incident results are ESP32 test data.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | cursor | integer | 否 | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | taskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | items | array | 是（所属对象出现时） | — | 本页记录&Current page of tasks, state events or test incidents. |
| 公共定义 | items[].taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | items[].state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | items[].error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | items[].revision | ['number', 'null'] | 否 | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | items[].priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | items[].executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | items[].created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | items[].updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | items[].stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | items[].progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | items[].feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | items[].result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | items[].result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | items[].result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | items[].result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | items[].result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | items[].result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | items[].result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | items[].result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | items[].result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | items[].result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | items[].result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | items[].result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | items[].result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | items[].result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | items[].result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | items[].result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | items[].result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | items[].result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | items[].result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | items[].result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | items[].result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | items[].result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | items[].result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | items[].result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | items[].result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | items[].result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | items[].result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | items[].result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | items[].result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | items[].result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | items[].cursor | integer | 否 | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | cursor | integer | 是（所属对象出现时） | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | more | boolean | 是（所属对象出现时） | — | 是否还有下一页&Whether another page is available after this cursor. |

#### Mesh_Task.Get_TaskList

List tasks&Returns caller-owned tasks using cursor pagination.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | cursor | integer | 否 | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | items | array | 是（所属对象出现时） | — | 本页记录&Current page of tasks, state events or test incidents. |
| 公共定义 | items[].taskId | ['string', 'null'] | 是（所属对象出现时） | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | items[].target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | items[].kind | ['string', 'null'] | 是（所属对象出现时） | — | 任务类型&Task type; selects the corresponding config and result contract. |
| 公共定义 | items[].state | ['string', 'null'] | 是（所属对象出现时） | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | items[].error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | items[].revision | ['number', 'null'] | 是（所属对象出现时） | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | items[].priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | items[].executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | items[].created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | items[].updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | items[].stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | items[].progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | items[].feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | items[].config | object | 否 | — | 任务配置&Task configuration; validated against kind or the stored task kind when updating. |
| 公共定义 | items[].config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Business value&See the method contract for meaning and constraints. |
| 公共定义 | items[].config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义 | items[].config.probeNodeId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义 | items[].config.watchTaskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义 | items[].config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义 | items[].config.executionMode | string | 否 | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | items[].config.areaId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义 | items[].config.pointIds | array | 否 | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义 | items[].config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义 | items[].config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义 | items[].config.eventId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | items[].config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf1 | items[].config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf1 | items[].config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | items[].config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf2 | items[].config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf2 | items[].config.probeNodeId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被检查节点&Authorized remote node to probe; cannot be the local root host. |
| 公共定义/anyOf3 | items[].config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义/anyOf3 | items[].config.periodMs | integer | 否 | {"minimum": 200, "maximum": 10000} | 采样周期&Sampling period in milliseconds; omission uses 1000. |
| 公共定义/anyOf3 | items[].config.watchTaskId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 被监视任务&Caller-accessible task to monitor; monitoring another monitor is prohibited. |
| 公共定义/anyOf3 | items[].config.staleAfterSeconds | integer | 否 | {"minimum": 1, "maximum": 3600} | Stale after seconds&Feedback freshness threshold in seconds; omission uses 10. |
| 公共定义/anyOf4 | items[].config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf4 | items[].config.areaId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,12}$"} | Area id&Logical test area identifier. |
| 公共定义/anyOf4 | items[].config.pointIds | array | 是（所属对象出现时） | {"minItems": 1, "maxItems": 3, "uniqueItems": true} | Point ids&Ordered distinct test point identifiers; no physical flight coordinates. |
| 公共定义/anyOf4 | items[].config.pointDurationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | Point duration seconds&Time spent on each test point in seconds; omission uses 3. |
| 公共定义/anyOf4 | items[].config.anomalyPoint | integer | 否 | {"minimum": 0, "maximum": 3} | Anomaly point&One-based test point producing an incident; zero disables incidents; omission uses zero. |
| 公共定义/anyOf5 | items[].config.executionMode | string | 是（所属对象出现时） | {"const": "esp32_test"} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义/anyOf5 | items[].config.eventId | string | 是（所属对象出现时） | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义/anyOf5 | items[].config.testVerdict | string | 否 | {"enum": ["confirmed", "cleared", "inconclusive"]} | Test verdict&Preset test review outcome; omission uses inconclusive. |
| 公共定义/anyOf5 | items[].config.durationSeconds | integer | 否 | {"minimum": 1, "maximum": 60} | 持续时间&Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review. |
| 公共定义 | items[].result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | items[].result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | items[].result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | items[].result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | items[].result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | items[].result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | items[].result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | items[].result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | items[].result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | items[].result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | items[].result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | items[].result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | items[].result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | items[].result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | items[].result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | items[].result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | items[].result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | items[].result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | items[].result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | items[].result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | items[].result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | items[].result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | items[].result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | items[].result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | items[].result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | items[].result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | items[].result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | items[].result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | items[].result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | items[].result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |
| 公共定义 | items[].lastOperation | object | 否 | — | Last operation&Last persisted control operation and dispatch state. |
| 公共定义 | items[].lastOperation.commandId | string | 否 | {"maxLength": 256} | Command id&Internal task operation identity returned as business tracking information. |
| 公共定义 | items[].lastOperation.op | string | 否 | {"maxLength": 256} | Op&Task control operation. |
| 公共定义 | items[].lastOperation.status | string | 否 | {"maxLength": 256} | Status&Observed device state or null if no observation exists. |
| 公共定义 | items[].lastOperation.opSeq | integer | 否 | {"minimum": 0} | Op seq&Monotonic task operation sequence. |
| 公共定义 | cursor | integer | 是（所属对象出现时） | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | more | boolean | 是（所属对象出现时） | — | 是否还有下一页&Whether another page is available after this cursor. |

#### Mesh_Task.Get_TestIncidents

Read events&Caller-owned durable history; incident results are ESP32 test data.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | cursor | integer | 否 | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | taskId | string | 否 | {"pattern": "^[A-Za-z0-9_-]{1,32}$", "minLength": 1, "maxLength": 32} | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |

**成功输出业务结果**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | items | array | 是（所属对象出现时） | — | 本页记录&Current page of tasks, state events or test incidents. |
| 公共定义 | items[].eventId | string | 否 | {"maxLength": 256} | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | items[].sourceTaskId | string | 否 | {"maxLength": 256} | Source task id&Task that generated this test incident. |
| 公共定义 | items[].nodeId | string | 否 | {"maxLength": 256} | Node id&Identity of the node described by this record. |
| 公共定义 | items[].areaId | string | 否 | {"maxLength": 256} | Area id&Logical test area identifier. |
| 公共定义 | items[].pointId | string | 否 | {"maxLength": 256} | Point id&Test point that generated the incident. |
| 公共定义 | items[].created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | items[].test | boolean | 否 | — | Test&True for ESP32 test incidents; not evidence of real-world detection. |
| 公共定义 | items[].executionMode | string | 否 | {"maxLength": 256} | Execution mode&Execution mode; esp32_test indicates a workflow test, not physical motion or recognition. |
| 公共定义 | cursor | integer | 是（所属对象出现时） | {"minimum": 0, "maximum": 9223372036854775807} | 查询游标&Durable pagination or replay cursor; zero starts from the beginning. |
| 公共定义 | more | boolean | 是（所属对象出现时） | — | 是否还有下一页&Whether another page is available after this cursor. |

#### Mesh_Task.Ntf_TaskChanged

Task change&One-way persisted state notification, not a control request.

**输入业务参数或发布载荷**

| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 公共定义 | taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | revision | ['number', 'null'] | 否 | — | Revision&Current task or parent policy revision; these revision domains are independent. |
| 公共定义 | priority | ['number', 'null'] | 否 | — | Priority&Queue priority from 0 through 9; omission uses zero. |
| 公共定义 | executeBefore | ['number', 'null'] | 否 | — | Execute before&Latest allowed execution start as Unix seconds; null means no such deadline. |
| 公共定义 | created | ['number', 'null'] | 否 | — | Created&Creation time as Unix seconds. |
| 公共定义 | updated | ['number', 'null'] | 否 | — | Updated&Last persisted change as Unix seconds. |
| 公共定义 | stateSeq | ['number', 'null'] | 否 | — | State seq&Monotonic state-change sequence for replay ordering. |
| 公共定义 | progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | feedbackAt | ['number', 'null'] | 否 | — | Feedback at&Host receive time of valid executor feedback as Unix seconds. |
| 公共定义 | result | object | 否 | — | 业务结果&Recorded metrics or ESP32 workflow result; absent until reported. |
| 公共定义 | result.source | ['string', 'null'] | 否 | — | Source&Metrics source: c6 or ugv_host. |
| 公共定义 | result.nodeId | ['string', 'null'] | 否 | — | Node id&Identity of the node described by this record. |
| 公共定义 | result.taskId | ['string', 'null'] | 否 | — | 任务编号&Stable task identity; supplied by the caller on creation to support querying uncertain submissions. |
| 公共定义 | result.target | ['string', 'null'] | 否 | — | Target&Task executor identity, or monitored task executor in a result. |
| 公共定义 | result.state | ['string', 'null'] | 否 | — | 当前状态&Known task or policy state; accepted does not mean physical execution completed. |
| 公共定义 | result.health | ['string', 'null'] | 否 | — | Health&Monitor health classification, distinct from task execution state. |
| 公共定义 | result.error | ['string', 'null'] | 否 | — | Error&Known operation or execution error; null means no recorded error. |
| 公共定义 | result.mode | ['string', 'null'] | 否 | — | 选择模式&Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode. |
| 公共定义 | result.stage | ['string', 'null'] | 否 | — | Stage&Processing stage, including acceptance versus final application or test progress. |
| 公共定义 | result.point | ['string', 'null'] | 否 | — | Point&Current ESP32 test point identity. |
| 公共定义 | result.eventId | ['string', 'null'] | 否 | — | Event id&Incident identity used to correlate the original test and review. |
| 公共定义 | result.verdict | ['string', 'null'] | 否 | — | Verdict&Reported test review conclusion, not actual recognition. |
| 公共定义 | result.samples | ['number', 'null'] | 否 | — | Samples&Number of collected diagnostic samples. |
| 公共定义 | result.readyNodes | ['number', 'null'] | 否 | — | Ready nodes&Number of ready nodes observed by host diagnostics. |
| 公共定义 | result.ok | ['number', 'null'] | 否 | — | Ok&Successful network probe count. |
| 公共定义 | result.failed | ['number', 'null'] | 否 | — | Failed&Failed network probe count. |
| 公共定义 | result.lastMs | ['number', 'null'] | 否 | — | Last ms&Latest application round-trip milliseconds; null on failure or before a successful measurement. |
| 公共定义 | result.avgMs | ['number', 'null'] | 否 | — | Avg ms&Mean successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | result.maxMs | ['number', 'null'] | 否 | — | Max ms&Maximum successful probe round-trip milliseconds, or null when none succeeded. |
| 公共定义 | result.ageS | ['number', 'null'] | 否 | — | Age s&Valid feedback or snapshot age in seconds. |
| 公共定义 | result.progress | ['number', 'null'] | 否 | — | Progress&Reported execution progress in percent. |
| 公共定义 | result.done | ['number', 'null'] | 否 | — | Done&Completed ESP32 test point count. |
| 公共定义 | result.total | ['number', 'null'] | 否 | — | Total&Total ESP32 test point count. |
| 公共定义 | result.rssi | ['number', 'null'] | 否 | — | Rssi&Reported Wi-Fi received signal strength in dBm. |
| 公共定义 | result.rssiMin | ['number', 'null'] | 否 | — | Rssi min&Minimum sampled RSSI in dBm. |
| 公共定义 | result.rssiMax | ['number', 'null'] | 否 | — | Rssi max&Maximum sampled RSSI in dBm. |
| 公共定义 | result.heap | ['number', 'null'] | 否 | — | Heap&Current free heap in bytes. |
| 公共定义 | result.heapMin | ['number', 'null'] | 否 | — | Heap min&Minimum free heap in bytes. |
| 公共定义 | result.ready | ['boolean', 'null'] | 否 | — | Ready&Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet. |

**成功输出业务结果**

`outputSchema: null`：单向消息没有业务响应，不应作为请求—响应方法调用。

## 重新生成

在主仓库执行 `uv run --locked python tools/export_mci_reference.py`。目录或 Schema 修改后应重新生成；运行中服务仍需由部署方重启才能加载代码。
