import sys
import os
import tempfile
import wave
import json
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
        
        full_text = ' '.join(result)
        if full_text.strip():
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