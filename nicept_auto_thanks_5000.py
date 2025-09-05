#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动运行5000种子感谢任务 - 无需用户交互
"""

import requests
import re
import time
import random
import json
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime

class AutoRun5000:
    def __init__(self):
        """初始化自动运行处理器"""
        self.session = requests.Session()
        self.base_url = "https://www.nicept.net"
        
        # Cookie
        cookie_value = "xxx"
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        })
        
        self.session.cookies.set('c_secure_pass', cookie_value, domain='www.nicept.net')
        
        # 统计
        self.processed = 0
        self.success = 0
        self.already_thanked = 0
        self.failed = 0
        self.start_time = datetime.now()
        
        # 进度文件
        self.progress_file = 'auto_progress.json'
        
        print("🚀 自动5000种子感谢任务启动")
        print(f"🕒 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    def save_progress(self):
        """保存进度到文件"""
        progress_data = {
            'processed': self.processed,
            'success': self.success,
            'already_thanked': self.already_thanked,
            'failed': self.failed,
            'start_time': self.start_time.isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    def get_torrents_from_page(self, page):
        """从指定页面获取种子列表"""
        try:
            url = f"{self.base_url}/torrents.php"
            if page > 0:
                url += f"?page={page}"
            
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            torrents = []
            
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'details.php?id=' in href and 'userdetails.php' not in href:
                    text = link.get_text(strip=True)
                    if text and len(text) > 5:
                        match = re.search(r'id=(\d+)', href)
                        if match:
                            torrent_id = match.group(1)
                            torrents.append({
                                'id': torrent_id,
                                'title': text[:50] + '...' if len(text) > 50 else text
                            })
            
            # 去重
            unique_torrents = []
            seen = set()
            for t in torrents:
                if t['id'] not in seen:
                    seen.add(t['id'])
                    unique_torrents.append(t)
            
            return unique_torrents
            
        except Exception as e:
            print(f"❌ 获取第{page+1}页失败: {e}")
            return []
    
    def process_torrent(self, torrent_id):
        """处理单个种子"""
        try:
            # 获取详情页
            detail_url = f"{self.base_url}/details.php?id={torrent_id}"
            response = self.session.get(detail_url, timeout=15)
            response.raise_for_status()
            
            content = response.text
            
            # 检查是否有感谢功能
            if 'saythanks(' not in content:
                return False, "无感谢功能"
            
            # 检查是否已感谢
            if re.search(r'id=["\']saythanks["\'][^>]*disabled', content):
                return False, "已感谢"
            
            # 发送感谢请求
            thanks_data = {'id': torrent_id}
            thanks_headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': detail_url
            }
            
            thanks_response = self.session.post(
                f"{self.base_url}/thanks.php",
                data=thanks_data,
                headers=thanks_headers,
                timeout=10
            )
            
            if thanks_response.status_code == 200:
                return True, "感谢成功"
            else:
                return False, f"请求失败({thanks_response.status_code})"
                
        except Exception as e:
            return False, f"处理失败: {e}"
    
    def run_auto_5000(self):
        """自动运行5000种子感谢"""
        print(f"🎯 目标: 自动处理5000个种子")
        print(f"⚡ 策略: 已感谢种子不延迟，成功感谢延迟1-5秒")
        print()
        
        current_page = 0
        
        try:
            while self.processed < 5000:
                # 获取当前页种子
                print(f"📄 正在获取第{current_page+1}页种子...")
                torrents = self.get_torrents_from_page(current_page)
                
                if not torrents:
                    print(f"⚠️ 第{current_page+1}页无种子，跳过")
                    current_page += 1
                    if current_page > 200:  # 防止无限循环
                        print("❌ 已扫描超过200页，停止")
                        break
                    continue
                
                print(f"✅ 第{current_page+1}页获取到{len(torrents)}个种子")
                
                for torrent in torrents:
                    if self.processed >= 5000:
                        break
                    
                    self.processed += 1
                    remaining = 5000 - self.processed
                    
                    print(f"[{self.processed}/5000] {torrent['title']}")
                    
                    success, message = self.process_torrent(torrent['id'])
                    
                    if success:
                        self.success += 1
                        print(f"  └─ ✅ {message}")
                        
                        # 只有成功时才延迟
                        if self.processed < 5000:
                            delay = random.uniform(1, 5)
                            print(f"  └─ 等待 {delay:.1f}s (剩余{remaining}个)")
                            time.sleep(delay)
                    else:
                        if "已感谢" in message:
                            self.already_thanked += 1
                        else:
                            self.failed += 1
                        print(f"  └─ ⏭️ {message}")
                        # 不延迟，直接继续
                    
                    # 每50个保存进度和显示统计
                    if self.processed % 50 == 0:
                        self.save_progress()
                        elapsed = datetime.now() - self.start_time
                        rate = self.processed / elapsed.total_seconds() * 60  # 每分钟处理数
                        print(f"📊 进度: {self.processed}/5000 | 成功:{self.success} | 已感谢:{self.already_thanked} | 失败:{self.failed} | 速度:{rate:.1f}/分钟")
                        print("-" * 60)
                
                # 翻页
                current_page += 1
                if self.processed < 5000:
                    print("📖 翻页中...")
                    time.sleep(random.uniform(2, 4))
        
        except KeyboardInterrupt:
            print("\n⏸️ 任务被用户中断")
        except Exception as e:
            print(f"❌ 任务执行出错: {e}")
        
        # 最终统计
        self.save_progress()
        end_time = datetime.now()
        elapsed = end_time - self.start_time
        
        print("\n" + "="*60)
        print("🎉 5000种子感谢任务完成!")
        print("="*60)
        print(f"总处理数: {self.processed}")
        print(f"成功感谢: {self.success}")
        print(f"已感谢过: {self.already_thanked}")
        print(f"处理失败: {self.failed}")
        print(f"开始时间: {self.start_time.strftime('%H:%M:%S')}")
        print(f"结束时间: {end_time.strftime('%H:%M:%S')}")
        print(f"总耗时: {elapsed}")
        
        if self.processed > 0:
            success_rate = (self.success / self.processed) * 100
            avg_speed = self.processed / elapsed.total_seconds() * 60
            print(f"成功率: {success_rate:.1f}%")
            print(f"平均速度: {avg_speed:.1f} 个/分钟")
        
        print("="*60)
        print(f"📁 进度文件已保存: {self.progress_file}")
        
        return self.processed, self.success


if __name__ == "__main__":
    try:
        auto_runner = AutoRun5000()
        processed, success = auto_runner.run_auto_5000()
        
        print(f"\n🏁 任务执行完毕！")
        print(f"处理了 {processed} 个种子，成功感谢 {success} 个")
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

