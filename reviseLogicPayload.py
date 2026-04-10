import json
import re
import os

# environment - 可以根据需要修改
gatewayRef1 = "XPlateform:KNX/KNX_GATEWAY-25086"
replace = {'0:0:13':'switch8_w', '0:1:1':'switch8_r', 
           '0:0:14':'switch14_w', '0:1:2':'switch14_r',
           '0:0:17':'switch17_w', '0:1:5':'switch17_r',
           '0:0:18':'switch18_w', '0:1:6':'switch18_r'
           }  # 可以随时扩充
dpt = {'1.001': '{{$.100.element}}', 
       '1.002': '{{$.100.element}}'
       } # 可以补充其它dpt子类

# 全局变量，用于存储从importLogic中提取的真实ID列表
real_ids = []

def importLogic(payload_json):
    global real_ids
    real_ids = []  # 重置列表
    
    try:
        # 解析JSON
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        return f"JSON解析错误 (import_payload): {e}"
    
    # 检查是否有nodes字段
    if 'nodes' not in payload:
        return "错误: import_payload 中没有 'nodes' 字段"
    
    # 遍历所有节点，收集真实的ID
    for node in payload['nodes']:
        if 'id' in node:
            real_ids.append(node['id'])
    
    # 遍历所有节点进行替换
    for node in payload['nodes']:
        # 1. 处理referenceId字段
        if 'referenceId' in node:
            ref_id = node['referenceId']
            # 找到第二个冒号的位置
            first_colon = ref_id.find(':')
            second_colon = ref_id.find(':', first_colon + 1)
            
            if second_colon != -1:
                prefix = ref_id[:second_colon]
                suffix = ref_id[second_colon + 1:]
                
                new_prefix = "{{gatewayRef1}}"
                
                if suffix in replace:
                    new_suffix = f"{{{{{replace[suffix]}}}}}"
                else:
                    new_suffix = suffix
                
                node['referenceId'] = f"{new_prefix}:{new_suffix}"
        
        # 2. 处理所有id字段（节点的id）
        if 'id' in node:
            node['id'] = node['id'] + "{{timestamp}}"
        
        # 3. 处理targetLinks中的sourceId和targetId
        if 'targetLinks' in node and node['targetLinks']:
            for link in node['targetLinks']:
                if 'sourceId' in link:
                    link['sourceId'] = link['sourceId'] + "{{timestamp}}"
                if 'targetId' in link:
                    link['targetId'] = link['targetId'] + "{{timestamp}}"
        
        # 4. 处理wires数组中的id引用
        if 'wires' in node and node['wires']:
            for wire_list in node['wires']:
                for i, wire_id in enumerate(wire_list):
                    wire_list[i] = wire_id + "{{timestamp}}"
        
        # 5. 处理 dataType 字段
        if 'dataType' in node:
            data_type_value = node['dataType']
            if data_type_value in dpt:
                node['dataType'] = dpt[data_type_value]
    
    # 返回修改后的JSON字符串
    return json.dumps(payload, indent=4, ensure_ascii=False)

def addLogic(payload_json):
    global real_ids
    
    try:
        # 解析JSON
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        return f"JSON解析错误 (add_payload): {e}"
    
    # 检查必要字段
    if 'ruleId' not in payload:
        return "错误: add_payload 中没有 'ruleId' 字段"
    if 'rule' not in payload:
        return "错误: add_payload 中没有 'rule' 字段"
    
    # 1. 获取ruleId的值
    rule_id_value = payload.get('ruleId', '')
    
    try:
        # 2. 解析rule字符串为JSON数组
        rule_array = json.loads(payload['rule'])
    except json.JSONDecodeError as e:
        return f"rule字段JSON解析错误: {e}"
    
    # 3. 遍历rule数组中的每个节点
    for node in rule_array:
        # 处理referenceId字段（和importLogic一样）
        if 'referenceId' in node:
            ref_id = node['referenceId']
            # 找到第二个冒号的位置
            first_colon = ref_id.find(':')
            second_colon = ref_id.find(':', first_colon + 1)
            
            if second_colon != -1:
                prefix = ref_id[:second_colon]
                suffix = ref_id[second_colon + 1:]
                
                new_prefix = "{{gatewayRef1}}"
                
                if suffix in replace:
                    new_suffix = f"{{{{{replace[suffix]}}}}}"
                else:
                    new_suffix = suffix
                
                node['referenceId'] = f"{new_prefix}:{new_suffix}"
        
        # 处理所有id字段
        if 'id' in node:
            node_id = node['id']
            # 如果id等于rule_id_value，替换为{{id_string}}
            if node_id == rule_id_value:
                node['id'] = "{{id_string}}"
            else:
                # 检查是否以real_ids中的某个ID开头
                matched = False
                for real_id in real_ids:
                    if node_id.startswith(real_id):
                        node['id'] = real_id + "{{timestamp}}"
                        matched = True
                        break
                if not matched:
                    # 如果没有匹配到，保持原样（可能不需要处理）
                    pass
        
        # 处理z字段（通常是ruleId的值）
        if 'z' in node and node['z'] == rule_id_value:
            node['z'] = "{{id_string}}"
        
        # 处理targetLinks中的sourceId和targetId
        if 'targetLinks' in node and node['targetLinks']:
            for link in node['targetLinks']:
                if 'sourceId' in link:
                    source_id = link['sourceId']
                    for real_id in real_ids:
                        if source_id.startswith(real_id):
                            link['sourceId'] = real_id + "{{timestamp}}"
                            break
                if 'targetId' in link:
                    target_id = link['targetId']
                    for real_id in real_ids:
                        if target_id.startswith(real_id):
                            link['targetId'] = real_id + "{{timestamp}}"
                            break
        
        # 处理wires数组中的id引用
        if 'wires' in node and node['wires']:
            for wire_list in node['wires']:
                for i, wire_id in enumerate(wire_list):
                    if wire_id == rule_id_value:
                        wire_list[i] = "{{id_string}}"
                    else:
                        for real_id in real_ids:
                            if wire_id.startswith(real_id):
                                wire_list[i] = real_id + "{{timestamp}}"
                                break

        # 处理dataType数组
        if 'dataType' in node:
            data_type_value = node['dataType']
            if data_type_value in dpt:
                node['dataType'] = dpt[data_type_value]
    
    # 4. 将修改后的rule_array转换回JSON字符串
    payload['rule'] = json.dumps(rule_array, ensure_ascii=False)
    
    # 5. 处理ruleId字段
    payload['ruleId'] = "{{id_string}}"
    
    # 返回修改后的JSON字符串
    return json.dumps(payload, indent=4, ensure_ascii=False)

def process_pair(import_text, add_text, output_file=None):
    """处理一对import和add payload"""
    print("\n" + "="*60)
    print("开始处理...")
    
    # 处理import
    print("处理 import_payload...")
    import_result = importLogic(import_text)
    if import_result.startswith("错误") or import_result.startswith("JSON解析错误"):
        print(f"import处理失败: {import_result}")
        return False
    
    print(f"提取到 {len(real_ids)} 个真实ID: {real_ids}")
    
    # 处理add
    print("处理 add_payload...")
    add_result = addLogic(add_text)
    if add_result.startswith("错误") or add_result.startswith("JSON解析错误"):
        print(f"add处理失败: {add_result}")
        return False
    
    # 输出结果
    print("\n" + "-"*60)
    print("处理成功！")
    print("-"*60)
    
    print("\n【importLogic 输出】:")
    print(import_result)
    
    print("\n【addLogic 输出】:")
    print(add_result)
    
    # 保存到文件
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("importLogic 输出:\n")
                f.write("="*60 + "\n")
                f.write(import_result + "\n\n")
                f.write("="*60 + "\n")
                f.write("addLogic 输出:\n")
                f.write("="*60 + "\n")
                f.write(add_result + "\n")
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"\n保存文件失败: {e}")
    
    return True

def main():
    print("="*60)
    print("KNX Logic 转换工具")
    print("="*60)
    print("\n使用说明:")
    print("1. 将 import_payload JSON 文本粘贴到下方")
    print("2. 将 add_payload JSON 文本粘贴到下方")
    print("3. 程序会自动处理并输出结果")
    print("4. 输入 'quit' 或 'exit' 退出程序")
    print("="*60)
    
    while True:
        print("\n" + "-"*60)
        
        # 获取import_payload
        print("\n请输入 import_payload (JSON格式):")
        print("(输入完成后，在新的一行输入 'END' 结束输入)")
        import_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            import_lines.append(line)
        
        if not import_lines:
            cmd = input("\n是否退出？(y/n): ").lower()
            if cmd == 'y':
                print("再见！")
                break
            continue
        
        import_text = '\n'.join(import_lines)
        
        # 获取add_payload
        print("\n请输入 add_payload (JSON格式):")
        print("(输入完成后，在新的一行输入 'END' 结束输入)")
        add_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            add_lines.append(line)
        
        if not add_lines:
            print("错误: add_payload 不能为空")
            continue
        
        add_text = '\n'.join(add_lines)
        
        # 询问是否保存到文件
        save_choice = input("\n是否保存结果到文件？(y/n): ").lower()
        output_file = None
        if save_choice == 'y':
            default_filename = f"knx_logic_output_{int(os.times().system)}.txt"
            filename = input(f"请输入文件名 (默认: {default_filename}): ").strip()
            if not filename:
                filename = default_filename
            output_file = filename
        
        # 处理
        process_pair(import_text, add_text, output_file)
        
        # 询问是否继续
        continue_choice = input("\n是否继续处理下一对？(y/n): ").lower()
        if continue_choice != 'y':
            print("再见！")
            break

def batch_process_from_file(input_file, output_file=None):
    """从文件批量处理"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 假设文件格式: 第一行是import_payload，第二行是add_payload
        lines = content.strip().split('\n')
        if len(lines) < 2:
            print("文件格式错误: 需要至少两行，第一行是import_payload，第二行是add_payload")
            return False
        
        import_text = lines[0].strip()
        add_text = lines[1].strip()
        
        if not output_file:
            output_file = input_file.replace('.txt', '_output.txt')
        
        return process_pair(import_text, add_text, output_file)
    
    except Exception as e:
        print(f"读取文件失败: {e}")
        return False

if __name__ == "__main__":
    # 检查是否批量处理模式
    import sys
    
    if len(sys.argv) > 1:
        # 批量处理模式
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        print(f"批量处理模式: 读取 {input_file}")
        batch_process_from_file(input_file, output_file)
    else:
        # 交互模式
        try:
            main()
        except KeyboardInterrupt:
            print("\n\n程序被用户中断，再见！")