import sys
import os
import tempfile
import wave
import json
import sys
from pydub import AudioSegment

def extract_audio(video_path):
    try:
        # 加载视频文件
        video = AudioSegment.from_file(video_path)
        
        # 提取音频并转换为Vosk所需格式 (16kHz, 16-bit, mono WAV)
        audio = video.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, 'temp_audio.wav')
        
        # 导出为WAV格式
        audio.export(audio_path, format='wav')
        
        return audio_path
    except Exception as e:
        print(f"音频提取失败: {str(e)}")
        return None


def audio_to_text(audio_path):
    # 完全离线模式：仅使用Vosk离线语音识别
    try:
        import vosk
        from vosk import Model, KaldiRecognizer
    except ImportError:
        print("离线语音识别引擎未安装，请执行以下命令安装:")
        print("pip install vosk")
        return None
    
    try:
        # 检查Vosk模型是否存在
        model_path = os.path.expanduser("~/.vosk/model-small-cn")
        
        # 检查模型目录是否存在
        if not os.path.exists(model_path):
            print(f"错误: 模型目录不存在 - {model_path}")
            print("请按照以下步骤重新安装模型:")
            print("1. 确保已安装wget和unzip: brew install wget unzip")
            print("2. 创建模型目录: mkdir -p ~/.vosk")
            print("3. 下载模型: wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip -O ~/.vosk/model-small-cn.zip")
            print("4. 解压模型: unzip ~/.vosk/model-small-cn.zip -d ~/.vosk/")
            print("5. 重命名模型目录: mv ~/.vosk/vosk-model-small-cn-0.22 ~/.vosk/model-small-cn")
            return None
        
        # 检查模型目录结构和关键文件
        # 检查必要目录
        required_dirs = ['am', 'conf', 'graph', 'ivector', 'rescore', 'rnnlm']
        missing_dirs = [d for d in required_dirs if not os.path.exists(os.path.join(model_path, d))]
        
        # 检查旧版本关键文件
        required_files_old = ['am/final.mdl']
        missing_files_old = [f for f in required_files_old if not os.path.exists(os.path.join(model_path, f))]
        
        # 检查新版本rnnlm目录下的关键文件
        rnnlm_path = os.path.join(model_path, 'rnnlm')
        required_rnnlm_files = ['final.raw', 'word_feats.txt']
        missing_rnnlm_files = [f for f in required_rnnlm_files if not os.path.exists(os.path.join(rnnlm_path, f))]
        
        # 综合判断模型完整性
        if missing_dirs and missing_files_old and missing_rnnlm_files:
            print("错误: 模型结构不完整，缺少必要的目录和文件")
            print(f"缺少的目录: {', '.join(missing_dirs)}")
            print(f"缺少的旧版本文件: {', '.join(missing_files_old)}")
            print(f"缺少的rnnlm文件: {', '.join(missing_rnnlm_files)}")
            print("故障排除建议:")
            print("1. 确认模型压缩包已正确解压: unzip -t ~/.vosk/model-small-cn.zip")
            print("2. 检查文件权限: ls -l {model_path}")
            print("3. 检查模型目录结构: find {model_path} -type d | sort")
            print("4. 尝试重新下载模型: rm ~/.vosk/model-small-cn.zip && wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip -O ~/.vosk/model-small-cn.zip")
            return None
        elif missing_files_old and missing_rnnlm_files:
            # 目录存在但关键文件都缺失
            print("错误: 模型文件不完整")
            print(f"缺少的旧版本文件: {', '.join(missing_files_old)}")
            print(f"缺少的rnnlm文件: {', '.join(missing_rnnlm_files)}")
            print("故障排除建议:")
            print("1. 确认模型压缩包已正确解压: unzip -t ~/.vosk/model-small-cn.zip")
            print("2. 检查模型文件: find {model_path} -type f | sort")
            return None
        elif missing_files_old and not missing_rnnlm_files:
            # 新版本模型结构，缺少旧版本文件但rnnlm文件存在
            print("警告: 未找到旧版本模型文件，但检测到新版本模型结构")
            print(f"缺少的旧版本文件: {', '.join(missing_files_old)}")
            print("这可能是由于模型版本更新导致的结构变化")
            print("继续尝试加载模型...")
        elif not missing_files_old and missing_rnnlm_files:
            # 旧版本模型结构，am/final.mdl存在但rnnlm文件缺失
            print("警告: 检测到旧版本模型结构，但缺少新版本rnnlm文件")
            print(f"缺少的rnnlm文件: {', '.join(missing_rnnlm_files)}")
            print("这可能是由于模型版本不匹配导致的")
            print("继续尝试加载模型...")
        
        # 打开音频文件
        wf = wave.open(audio_path, "rb")
        
        # 加载模型并识别
        model = Model(model_path)
        rec = KaldiRecognizer(model, wf.getframerate())
        result = []
        
        print("正在进行离线语音识别...")
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                if 'text' in res and res['text']:
                    result.append(res['text'])
        
        final_res = json.loads(rec.FinalResult())
        if 'text' in final_res and final_res['text']:
            result.append(final_res['text'])
        
        full_text = ''.join(result)
        if full_text.strip():
            # 添加标点符号
            try:
                import sys
                print(f"当前Python版本: {sys.version}")
                print(f"尝试导入pyhanlp库...")
                from pyhanlp import HanLP
                print("pyhanlp库导入成功")
                # 使用HanLP添加标点符号
                # 尝试不同的方法名称，因为不同版本可能有差异
                # 改进的标点符号处理逻辑
                
                # 首先尝试方法1: addPunctuation
                try:
                    punctuated_text = HanLP.addPunctuation(full_text)
                    print("使用addPunctuation方法添加标点")
                    # 移除可能的转义符
                    punctuated_text = punctuated_text.replace('/w', '').replace('/n', '').replace('/ude1', '').replace('/d', '').replace('/vshi', '').replace('/rr', '').replace('/ule', '').replace('/a', '')
                except AttributeError:
                    # 尝试方法2: punctuate
                    try:
                        punctuated_text = HanLP.punctuate(full_text)
                        print("使用punctuate方法添加标点")
                        # 移除可能的转义符
                        punctuated_text = punctuated_text.replace('/w', '').replace('/n', '').replace('/ude1', '').replace('/d', '').replace('/vshi', '').replace('/rr', '').replace('/ule', '').replace('/a', '')
                    except AttributeError:
                        # 方法3: 改进的分词后手动添加标点逻辑
                        print("尝试使用改进的分词后手动添加标点...")
                        words = HanLP.segment(full_text)
                        if words:
                            # 只保留词语部分，去除词性标记
                            pure_words = [str(word).split('/')[0] for word in words]
                            
                            # 改进的标点符号添加逻辑
                            # 1. 基本连接
                            punctuated_text = ''.join(pure_words)
                            
                            # 2. 添加简单标点 - 在逗号、句号等位置添加
                            # 这是一个简单的规则，实际应用可能需要更复杂的NLP分析
                            # 这里我们基于一些常见的标点位置模式添加标点
                            import re
                            # 添加逗号
                            punctuated_text = re.sub(r'([，,])', r'\1', punctuated_text)  # 保留已有逗号
                            # 添加句号
                            if not punctuated_text.endswith(('。', '！', '？', '.')):
                                punctuated_text += '。'
                            
                            # 3. 尝试在句子中间添加更多标点
                            # 这里使用简单的规则：在特定词性后面添加标点
                            # 注意：这只是一个基础实现，实际效果可能有限
                            pos_words = [(str(word).split('/')[0], str(word).split('/')[1]) for word in words if len(str(word).split('/')) > 1]
                            if pos_words:
                                enhanced_text = []
                                for i, (word, pos) in enumerate(pos_words):
                                    enhanced_text.append(word)
                                    # 在名词、代词后可能需要添加标点
                                    if pos in ['n', 'nr', 'ns', 'nt', 'nz', 'r'] and i < len(pos_words) - 1:
                                        next_word, next_pos = pos_words[i+1]
                                        # 如果下一个词不是虚词或标点，添加逗号
                                        if next_pos not in ['u', 'p', 'c', 'd', 'm'] and next_word not in ['，', '。', '！', '？', ',', '.', '!', '?']:
                                            enhanced_text.append('，')
                                punctuated_text = ''.join(enhanced_text)
                                # 确保句末有标点
                                if not punctuated_text.endswith(('。', '！', '？', '.')):
                                    punctuated_text += '。'
                        else:
                            punctuated_text = full_text
                            if not punctuated_text.endswith(('。', '！', '？', '.')):
                                punctuated_text += '。'
                # 去除所有不必要的空格
                punctuated_text = punctuated_text.replace(' ', '')
                return punctuated_text
            except ImportError as e:
                print(f"警告: 无法导入pyhanlp库: {str(e)}")
                print("如需添加标点符号，请确保已正确安装pyhanlp:")
                print("1. 执行: pip install pyhanlp")
                print("2. 如已安装，可能是Python环境问题，尝试创建虚拟环境:")
                print("   python -m venv venv")
                print("   source venv/bin/activate")
                print("   pip install pyhanlp")
                print("3. 检查Python版本是否兼容(推荐Python 3.6-3.9)")
                print("4. 检查是否有多个Python版本共存导致的问题")
                # 去除所有不必要的空格
                full_text = full_text.replace(' ', '')
                return full_text
            except Exception as e:
                print(f"添加标点符号时出错: {str(e)}")
                error_msg = str(e).lower()
                if 'java' in error_msg:
                    print("错误原因: Java运行时环境问题")
                    if 'jvm dll not found' in error_msg:
                        print("具体问题: 无法找到JVM DLL文件，可能是Java环境变量未配置正确")
                        print("请按照以下步骤配置Java环境:")
                        print("1. 确认Java安装路径，通常为: /Library/Java/JavaVirtualMachines/jdk-xx.jdk/Contents/Home")
                        print("2. 打开终端，执行命令: echo 'export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-xx.jdk/Contents/Home' >> ~/.zshrc")
                        print("   (注意替换为你的实际Java安装路径)")
                        print("3. 执行命令: source ~/.zshrc 更新环境变量")
                        print("4. 执行命令: echo $JAVA_HOME 验证环境变量是否设置成功")
                        print("5. 重新运行本脚本")
                    elif 'restricted method' in error_msg:
                        print("具体问题: Java安全限制导致的方法调用问题")
                        print("解决方法: 尝试使用以下命令运行脚本:")
                        print("   java -jar --enable-native-access=ALL-UNNAMED $(which python) xiaohongshu_audio_to_text.py")
                    else:
                        print("请按照以下步骤安装Java:")
                        print("1. 访问 http://www.java.com 获取最新Java运行时环境")
                        print("2. 安装完成后，重新运行本脚本")
                    print("3. 如需无Java依赖的标点符号功能，请告知我")
                elif 'attributeerror' in error_msg and ('addpunctuation' in error_msg or 'punctuate' in error_msg):
                    print("具体问题: pyhanlp库版本不兼容，找不到对应的标点符号方法")
                    print("解决方法:")
                    print("1. 尝试安装特定版本的pyhanlp: pip install pyhanlp==0.1.84")
                    print("2. 或者使用其他标点符号处理库，如pypinyin或jieba")
                return full_text
        else:
            print("离线语音识别未返回任何结果，请尝试:")
            print("1. 确保音频质量良好")
            print("2. 检查模型文件是否完整")
            print("3. 尝试重新安装Vosk模型")
            return None
    except Exception as e:
        print(f"离线语音识别失败: {str(e)}")
        print("故障排除建议:")
        print("1. 检查模型路径是否正确: ~/.vosk/model-small-cn")
        print("2. 验证模型文件是否完整")
        print("3. 确保音频文件格式正确")
        return None
    except sr.UnknownValueError:
        print("无法识别音频内容")
    except Exception as e:
        print(f"语音转文字失败: {e}")
    
    return None


def main():
    print("=== 完全离线视频语音转文字工具 ===")
    # 获取用户输入的本地视频文件路径
    video_path = input("请输入本地视频文件的绝对路径: ")
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 文件不存在 - {video_path}")
        sys.exit(1)
    
    # 检查文件是否为视频文件
    valid_extensions = ['.mp4', '.mov', '.avi', '.flv', '.mkv', '.wmv']
    if not any(video_path.lower().endswith(ext) for ext in valid_extensions):
        print(f"错误: 不支持的文件格式，请提供以下格式的视频文件: {', '.join(valid_extensions)}")
        sys.exit(1)
    
    # 获取用户指定的保存目录
    output_dir = input("请输入结果保存目录 (直接回车保存到当前目录): ").strip()
    if not output_dir:
        output_dir = os.getcwd()
    
    # 确保输出目录存在
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"结果将保存到目录: {output_dir}")
    except Exception as e:
        print(f"创建保存目录时出错: {str(e)}")
        sys.exit(1)
    
    # 提取音频
    audio_path = extract_audio(video_path)
    if not audio_path:
        print("错误: 音频提取失败，无法继续处理")
        sys.exit(1)
    
    # 语音转文字
    text = audio_to_text(audio_path)
    if not text:
        print("错误: 语音转文字失败，请检查音频质量或Vosk模型配置")
        sys.exit(1)
    
    print("\n=== 视频语音转文字结果 ===\n")
    print(text)

    # 保存结果到文件
    try:
        # 拼接输出文件路径
        output_file = os.path.join(output_dir, "audio_to_text.txt")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print(f"结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存结果到文件时出错: {str(e)}")

    # 清理临时文件
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)
        # 尝试删除临时目录
        temp_dir = os.path.dirname(audio_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass  # 目录不为空时忽略
    
    sys.exit(0)


if __name__ == "__main__":
    main()