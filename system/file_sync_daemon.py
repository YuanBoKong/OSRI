#!/usr/bin/env python3
"""
文件同步守护进程
监听 system/jsondata、system/jsondata_aggregation、system/output、system/output_aggregation 目录
当指定文件更新时，自动同步到 vis/data 和 vis/data_aggregation 目录
"""
import sys
import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# 需要同步的文件列表
SYNC_FILES = [
    'OA.json',
    'R_op_bar.json',
    'scientist.json',
    'cooperation.json',
    'R_oa_bar.json',
    'R.json',
    'R_od_bar.json',
    'retraction.json',
    'total.json'
]

# 目录映射关系
# 源目录 -> 目标目录
DIR_MAPPINGS = {
    'jsondata': 'data',
    'jsondata_aggregation': 'data_aggregation',
    'output': 'data',
    'output_aggregation': 'data_aggregation'
}


class FileSyncHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, source_dir: Path, target_dir: Path, sync_files: list):
        """
        初始化处理器
        
        Args:
            source_dir: 源目录路径
            target_dir: 目标目录路径
            sync_files: 需要同步的文件列表
        """
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.sync_files = set(sync_files)  # 使用 set 提高查找效率
        self.last_sync_time = {}  # 记录每个文件的最后同步时间，用于防抖
        
    def should_sync(self, file_path: Path) -> bool:
        """
        判断文件是否需要同步
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否需要同步
        """
        # 检查是否是目标文件
        if file_path.name not in self.sync_files:
            return False
        
        # 检查文件是否存在且是文件（不是目录）
        if not file_path.exists() or not file_path.is_file():
            return False
        
        return True
    
    def sync_file(self, file_path: Path):
        """
        同步文件到目标目录
        
        Args:
            file_path: 源文件路径
        """
        # 防抖：如果 1 秒内已经同步过，跳过（避免重复同步）
        current_time = time.time()
        if file_path in self.last_sync_time:
            if current_time - self.last_sync_time[file_path] < 1.0:
                return
        
        try:
            # 确保目标目录存在
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            # 目标文件路径
            target_file = self.target_dir / file_path.name
            
            # 复制文件（使用 shutil.copy2 保留元数据）
            shutil.copy2(file_path, target_file)
            
            # 更新最后同步时间
            self.last_sync_time[file_path] = current_time
            
            print(f"✓ 已同步: {file_path.name} ({file_path.parent.name} -> {self.target_dir.name})")
            
        except Exception as e:
            print(f"✗ 同步失败: {file_path.name} - {str(e)}")
    
    def on_modified(self, event: FileSystemEvent):
        """文件修改事件"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self.should_sync(file_path):
            self.sync_file(file_path)
    
    def on_created(self, event: FileSystemEvent):
        """文件创建事件"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self.should_sync(file_path):
            # 等待一小段时间，确保文件写入完成
            time.sleep(0.1)
            self.sync_file(file_path)
    
    def on_moved(self, event: FileSystemEvent):
        """文件移动/重命名事件（包括临时文件重命名）"""
        if event.is_directory:
            return
        
        # 处理目标文件（移动后的文件）
        if hasattr(event, 'dest_path') and event.dest_path:
            file_path = Path(event.dest_path)
            if self.should_sync(file_path):
                time.sleep(0.1)  # 等待文件写入完成
                self.sync_file(file_path)


def setup_observers(base_dir: Path) -> list:
    """
    设置文件系统观察者
    
    Args:
        base_dir: 项目根目录路径
        
    Returns:
        list: 观察者列表
    """
    observers = []
    
    # 源目录和目标目录
    system_dir = base_dir / 'system'
    vis_dir = base_dir / 'vis'
    
    # 为每个源目录创建观察者
    for source_subdir, target_subdir in DIR_MAPPINGS.items():
        source_dir = system_dir / source_subdir
        target_dir = vis_dir / target_subdir
        
        # 检查源目录是否存在
        if not source_dir.exists():
            print(f"警告: 源目录不存在，跳过: {source_dir}")
            continue
        
        # 创建事件处理器
        handler = FileSyncHandler(source_dir, target_dir, SYNC_FILES)
        
        # 创建观察者
        observer = Observer()
        observer.schedule(handler, str(source_dir), recursive=False)
        
        observers.append((observer, source_dir, target_dir))
        
        print(f"监听目录: {source_dir} -> {target_dir}")
    
    return observers


def initial_sync(base_dir: Path):
    """
    初始同步：启动时同步所有需要同步的文件
    
    Args:
        base_dir: 项目根目录路径
    """
    print("执行初始同步...")
    system_dir = base_dir / 'system'
    vis_dir = base_dir / 'vis'
    
    synced_count = 0
    
    for source_subdir, target_subdir in DIR_MAPPINGS.items():
        source_dir = system_dir / source_subdir
        target_dir = vis_dir / target_subdir
        
        if not source_dir.exists():
            continue
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 同步每个文件
        for filename in SYNC_FILES:
            source_file = source_dir / filename
            if source_file.exists() and source_file.is_file():
                try:
                    target_file = target_dir / filename
                    shutil.copy2(source_file, target_file)
                    synced_count += 1
                    print(f"✓ 初始同步: {filename} ({source_subdir} -> {target_subdir})")
                except Exception as e:
                    print(f"✗ 初始同步失败: {filename} - {str(e)}")
    
    print(f"初始同步完成，共同步 {synced_count} 个文件\n")


def main():
    """主函数"""
    # 获取项目根目录（脚本所在目录的父目录）
    script_dir = Path(__file__).parent.absolute()
    base_dir = script_dir.parent
    
    print("=" * 60)
    print("文件同步守护进程启动")
    print("=" * 60)
    print(f"项目根目录: {base_dir}")
    print(f"监听文件: {', '.join(SYNC_FILES)}")
    print()
    
    # 执行初始同步
    initial_sync(base_dir)
    
    # 设置观察者
    observers = setup_observers(base_dir)
    
    if not observers:
        print("错误: 没有可监听的目录，退出")
        sys.exit(1)
    
    # 启动所有观察者
    for observer, source_dir, target_dir in observers:
        observer.start()
        print(f"✓ 已启动监听: {source_dir}")
    
    print("\n守护进程运行中，按 Ctrl+C 停止...\n")
    
    try:
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止守护进程...")
        for observer, source_dir, target_dir in observers:
            observer.stop()
            print(f"✓ 已停止监听: {source_dir}")
        
        # 等待所有观察者停止
        for observer, source_dir, target_dir in observers:
            observer.join()
        
        print("守护进程已停止")


if __name__ == '__main__':
    main()

