"""Export actual MCI discovery JSON and Appendix A business-field reference."""
import json
from pathlib import Path
from changan_ugv.mci import MCI


def field_rows(schema, path='', branch='公共定义'):
    if not isinstance(schema,dict):return
    required=schema.get('required',[])
    for key,definition in schema.get('properties',{}).items():
        current=path+'.'+key if path else key
        constraints={k:v for k,v in definition.items() if k in
                     ('enum','const','minimum','maximum','minLength','maxLength','minItems','maxItems','uniqueItems','pattern','default')}
        yield [branch,current,str(definition.get('type',definition.get('$ref',''))),
               '是（所属对象出现时）' if key in required else '否',
               json.dumps(constraints,ensure_ascii=False) if constraints else '—',definition.get('description','')]
        yield from field_rows(definition,current,branch)
    if isinstance(schema.get('items'),dict):yield from field_rows(schema['items'],path+'[]',branch)
    for keyword in ('oneOf','anyOf','allOf'):
        for index,child in enumerate(schema.get(keyword,[]),1):
            kind=child.get('properties',{}).get('kind',{}).get('const')
            yield from field_rows(child,path,'kind='+kind if kind else branch+'/'+keyword+str(index))


def export(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    response=MCI(None).discover({})
    if 'error' in response:raise ValueError(response)
    raw=json.dumps(response,ensure_ascii=False,indent=2)+'\n'
    (destination/'listMethod-response.json').write_text(raw,encoding='utf-8')
    lines=['# 附录 A listMethod 返回示例与字段说明','',
           '本附录由当前实现的 `listMethod({})` 直接生成，描述4个服务、23个方法。不是调用请求，也不是 GUI 导出日志的外壳。',
           '业务方法的名称属于本项目约定；企业附录中的 Base_File、Loco_Robot 是格式示例，不要求实现相同业务。',
           '输入、输出及字段说明与实际发现响应一致；生成快照不会启动服务或连接现场设备。','',
           '## A.1 完整返回报文','',
           '以下为不带筛选条件的完整成功响应。可直接下载 [JSON 原文件](listMethod-response.json)。','',
           '```json',raw.rstrip(),'```','',
           '## A.2 业务 key 逐项说明','',
           '路径表示实际业务数据，不包含 `properties` 等 Schema 关键字。字段说明保留实际发布的“用户描述&详细描述”。',
           '必填性在所属对象内生效，子字段必填不等于父字段必填。分支行只在对应 kind 或 Schema 分支生效，公共约束仍同时适用。',
           'oneOf 要求恰好匹配一个分支；anyOf 要求至少匹配一个分支。Schema 的 default 不自动补值，运行时默认值以字段说明为准。','']
    for service in response['services']:
        lines+=['### '+service['service'],'']
        for method in service['methods']:
            lines+=['#### '+service['service']+'.'+method['method'],'',method['description'],'']
            for direction,key in [('输入业务参数或发布载荷','inputSchema'),('成功输出业务结果','outputSchema')]:
                lines+=['**'+direction+'**','']
                schema=method[key]
                if schema is None:
                    lines+=['`outputSchema: null`：单向消息没有业务响应，不应作为请求—响应方法调用。',''];continue
                rows=list(field_rows(schema))
                if not rows:lines+=['空对象 `{}`，没有业务字段，禁止额外字段。',''];continue
                lines+=['| 生效范围 | 业务字段路径 | 类型 | 必填 | 约束 | 说明 |','| --- | --- | --- | --- | --- | --- |']
                seen=set()
                for row in rows:
                    signature=tuple(row)
                    if signature in seen:continue
                    seen.add(signature)
                    lines+=['| '+' | '.join(x.replace('|','\\|').replace('\n',' ') for x in row)+' |']
                lines+=['']
    lines+=['## 重新生成','',
            '在主仓库执行 `uv run --locked python tools/export_mci_reference.py`。目录或 Schema 修改后应重新生成；运行中服务仍需由部署方重启才能加载代码。','']
    (destination/'appendix.md').write_text('\n'.join(lines),encoding='utf-8')
    return response


if __name__=='__main__':
    export(Path(__file__).resolve().parents[1]/'protocols/mci/v1')
    print('Exported listMethod-response.json and appendix.md')
