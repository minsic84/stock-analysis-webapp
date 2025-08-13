#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 자동 스케줄러
- 오전 8시 기준 날짜 처리
- 자동 데이터 수집 스케줄링
- 유연한 스케줄 관리
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import os

from .crawler import TopRateCrawler
from .utils import get_trading_date


class TopRateScheduler:
    """등락율상위분석 자동 스케줄러"""

    def __init__(self):
        """스케줄러 초기화"""
        self.scheduler = None
        self.is_running = False

        # 기본 스케줄 설정
        self.default_schedules = [
            {'hour': 9, 'minute': 15, 'enabled': True, 'name': '장시작후'},
            {'hour': 14, 'minute': 0, 'enabled': False, 'name': '오후2시'},
            {'hour': 17, 'minute': 30, 'enabled': False, 'name': '장마감후'}
        ]

        # 활성 스케줄 저장
        self.active_schedules = {}

        self._setup_scheduler()

    def _setup_scheduler(self):
        """스케줄러 설정"""
        try:
            # ThreadPool 실행자 설정
            executors = {
                'default': ThreadPoolExecutor(20),
            }

            # 작업 기본 설정
            job_defaults = {
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 300  # 5분 지연 허용
            }

            self.scheduler = BackgroundScheduler(
                executors=executors,
                job_defaults=job_defaults,
                timezone='Asia/Seoul'
            )

            logging.info("✅ 스케줄러 설정 완료")

        except Exception as e:
            logging.error(f"❌ 스케줄러 설정 실패: {e}")

    def init_app(self, app):
        """Flask 앱 초기화"""
        try:
            # 기본 스케줄 등록
            for schedule in self.default_schedules:
                if schedule['enabled']:
                    self.add_schedule(
                        hour=schedule['hour'],
                        minute=schedule['minute'],
                        name=schedule['name']
                    )

            # 개발 환경에서는 스케줄러 비활성화 (선택사항)
            if app.config.get('DEBUG', False) and not os.getenv('ENABLE_SCHEDULER'):
                logging.info("ℹ️ 개발 모드: 스케줄러 비활성화")
                return

            # 스케줄러 시작
            self.start()

            app.logger.info("✅ TopRateScheduler 초기화 완료")

        except Exception as e:
            app.logger.error(f"❌ TopRateScheduler 초기화 실패: {e}")

    def start(self):
        """스케줄러 시작"""
        try:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                logging.info("🚀 자동 스케줄러 시작")
            else:
                logging.info("ℹ️ 스케줄러가 이미 실행 중입니다")

        except Exception as e:
            logging.error(f"❌ 스케줄러 시작 실패: {e}")

    def stop(self):
        """스케줄러 중지"""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logging.info("⏹️ 자동 스케줄러 중지")
            else:
                logging.info("ℹ️ 스케줄러가 이미 중지되어 있습니다")

        except Exception as e:
            logging.error(f"❌ 스케줄러 중지 실패: {e}")

    def add_schedule(self, hour: int, minute: int, name: str = None) -> str:
        """
        스케줄 추가

        Args:
            hour: 시간 (0-23)
            minute: 분 (0-59)
            name: 스케줄 이름 (선택사항)

        Returns:
            추가된 작업 ID
        """
        try:
            if not self.scheduler:
                raise Exception("스케줄러가 초기화되지 않았습니다")

            # 작업 ID 생성
            job_id = f"auto_crawling_{hour:02d}_{minute:02d}"

            # 기존 작업이 있으면 제거
            if job_id in self.active_schedules:
                self.remove_schedule(job_id)

            # 새 스케줄 추가
            job = self.scheduler.add_job(
                func=self._scheduled_crawling,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job_id,
                name=name or f"자동수집 {hour:02d}:{minute:02d}",
                args=[name or f"{hour:02d}:{minute:02d}"]
            )

            # 활성 스케줄에 저장
            self.active_schedules[job_id] = {
                'hour': hour,
                'minute': minute,
                'name': name or f"{hour:02d}:{minute:02d}",
                'enabled': True,
                'next_run': job.next_run_time
            }

            logging.info(f"✅ 스케줄 추가: {name or job_id} ({hour:02d}:{minute:02d})")
            return job_id

        except Exception as e:
            logging.error(f"❌ 스케줄 추가 실패: {e}")
            return ""

    def remove_schedule(self, job_id: str) -> bool:
        """
        스케줄 제거

        Args:
            job_id: 제거할 작업 ID

        Returns:
            제거 성공 여부
        """
        try:
            if job_id in self.active_schedules:
                # 스케줄러에서 제거
                self.scheduler.remove_job(job_id)

                # 활성 스케줄에서 제거
                schedule_name = self.active_schedules[job_id]['name']
                del self.active_schedules[job_id]

                logging.info(f"✅ 스케줄 제거: {schedule_name}")
                return True
            else:
                logging.warning(f"제거할 스케줄을 찾을 수 없습니다: {job_id}")
                return False

        except Exception as e:
            logging.error(f"❌ 스케줄 제거 실패: {e}")
            return False

    def toggle_schedule(self, job_id: str) -> bool:
        """
        스케줄 활성화/비활성화 토글

        Args:
            job_id: 토글할 작업 ID

        Returns:
            토글 후 활성화 상태
        """
        try:
            if job_id not in self.active_schedules:
                logging.warning(f"토글할 스케줄을 찾을 수 없습니다: {job_id}")
                return False

            schedule = self.active_schedules[job_id]

            if schedule['enabled']:
                # 비활성화
                self.scheduler.pause_job(job_id)
                schedule['enabled'] = False
                status = "비활성화"
            else:
                # 활성화
                self.scheduler.resume_job(job_id)
                schedule['enabled'] = True
                status = "활성화"

            logging.info(f"🔄 스케줄 {status}: {schedule['name']}")
            return schedule['enabled']

        except Exception as e:
            logging.error(f"❌ 스케줄 토글 실패: {e}")
            return False

    def get_schedules(self) -> List[Dict]:
        """
        현재 스케줄 목록 조회

        Returns:
            스케줄 정보 리스트
        """
        schedules = []

        for job_id, schedule in self.active_schedules.items():
            try:
                # 스케줄러에서 실제 작업 정보 가져오기
                job = self.scheduler.get_job(job_id)

                schedule_info = {
                    'id': job_id,
                    'name': schedule['name'],
                    'time': f"{schedule['hour']:02d}:{schedule['minute']:02d}",
                    'enabled': schedule['enabled'],
                    'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job and job.next_run_time else None
                }

                schedules.append(schedule_info)

            except Exception as e:
                logging.warning(f"스케줄 정보 조회 실패 ({job_id}): {e}")
                continue

        # 시간순 정렬
        schedules.sort(key=lambda x: (x['time']))
        return schedules

    def _scheduled_crawling(self, schedule_name: str):
        """
        스케줄된 크롤링 실행

        Args:
            schedule_name: 스케줄 이름
        """
        start_time = datetime.now()

        try:
            # 거래일 기준 날짜 계산
            target_date = get_trading_date()

            logging.info(f"🤖 자동 크롤링 시작 ({schedule_name})")
            logging.info(f"📅 대상 날짜: {target_date}")

            # 크롤러 실행
            crawler = TopRateCrawler()
            success = crawler.crawl_and_save(target_date)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if success:
                logging.info(f"✅ 자동 크롤링 완료 ({schedule_name}, {duration:.1f}초)")
                self._send_notification(True, schedule_name, target_date, duration)
            else:
                logging.error(f"❌ 자동 크롤링 실패 ({schedule_name})")
                self._send_notification(False, schedule_name, target_date, duration, "크롤링 프로세스 실패")

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.error(f"❌ 자동 크롤링 오류 ({schedule_name}): {e}")
            self._send_notification(False, schedule_name, get_trading_date(), duration, str(e))

    def _send_notification(self, success: bool, schedule_name: str, date: str, duration: float, error: str = None):
        """
        크롤링 결과 알림 (확장 가능)

        Args:
            success: 성공 여부
            schedule_name: 스케줄 이름
            date: 크롤링 날짜
            duration: 소요 시간
            error: 오류 메시지 (실패시)
        """
        status = "성공" if success else "실패"
        message = f"[{schedule_name}] 등락율상위분석 {status} ({date}, {duration:.1f}초)"

        if not success and error:
            message += f" - {error}"

        # 여기에 추가 알림 로직 구현 가능
        # - 이메일 발송
        # - 슬랙 메시지
        # - 텔레그램 봇
        # - 웹훅 호출

        logging.info(f"📢 알림: {message}")

    def run_manual_crawling(self, target_date: str = None) -> bool:
        """
        수동 크롤링 실행

        Args:
            target_date: 대상 날짜 (None이면 거래일 기준)

        Returns:
            실행 성공 여부
        """
        try:
            if target_date is None:
                target_date = get_trading_date()

            logging.info(f"🖱️ 수동 크롤링 시작 (날짜: {target_date})")

            # 크롤러 실행
            crawler = TopRateCrawler()
            success = crawler.crawl_and_save(target_date)

            if success:
                logging.info(f"✅ 수동 크롤링 완료 (날짜: {target_date})")
            else:
                logging.error(f"❌ 수동 크롤링 실패 (날짜: {target_date})")

            return success

        except Exception as e:
            logging.error(f"❌ 수동 크롤링 오류: {e}")
            return False

    def get_next_run_times(self) -> Dict[str, str]:
        """
        다음 실행 시간 조회

        Returns:
            스케줄별 다음 실행 시간
        """
        next_runs = {}

        for job_id, schedule in self.active_schedules.items():
            try:
                job = self.scheduler.get_job(job_id)
                if job and job.next_run_time and schedule['enabled']:
                    next_runs[schedule['name']] = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    next_runs[schedule['name']] = "비활성화"

            except Exception:
                next_runs[schedule['name']] = "오류"

        return next_runs

    def is_holiday_or_weekend(self, date: datetime = None) -> bool:
        """
        휴일 또는 주말 여부 확인 (확장 가능)

        Args:
            date: 확인할 날짜 (None이면 오늘)

        Returns:
            휴일/주말 여부
        """
        if date is None:
            date = datetime.now()

        # 주말 체크 (토요일=5, 일요일=6)
        if date.weekday() >= 5:
            return True

        # 여기에 한국 공휴일 체크 로직 추가 가능
        # - 신정, 설날, 삼일절, 어린이날 등
        # - 외부 API 또는 라이브러리 활용

        return False

    def should_skip_crawling(self) -> Tuple[bool, str]:
        """
        크롤링 스킵 여부 판단

        Returns:
            (스킵여부, 사유)
        """
        now = datetime.now()

        # 휴일/주말 체크
        if self.is_holiday_or_weekend(now):
            return True, "휴일/주말"

        # 장외시간 체크 (선택사항)
        # 예: 새벽 1시-6시는 스킵
        if 1 <= now.hour < 6:
            return True, "장외시간"

        return False, ""

    def update_schedule_config(self, schedules: List[Dict]) -> bool:
        """
        스케줄 설정 업데이트

        Args:
            schedules: 새로운 스케줄 설정 리스트

        Returns:
            업데이트 성공 여부
        """
        try:
            # 기존 스케줄 모두 제거
            for job_id in list(self.active_schedules.keys()):
                self.remove_schedule(job_id)

            # 새 스케줄 추가
            for schedule in schedules:
                if schedule.get('enabled', False):
                    self.add_schedule(
                        hour=schedule['hour'],
                        minute=schedule['minute'],
                        name=schedule.get('name', f"{schedule['hour']:02d}:{schedule['minute']:02d}")
                    )

            logging.info(f"✅ 스케줄 설정 업데이트 완료: {len(schedules)}개")
            return True

        except Exception as e:
            logging.error(f"❌ 스케줄 설정 업데이트 실패: {e}")
            return False


# 전역 스케줄러 인스턴스 (선택사항)
global_scheduler = None


def get_scheduler():
    """전역 스케줄러 인스턴스 반환"""
    global global_scheduler
    if global_scheduler is None:
        global_scheduler = TopRateScheduler()
    return global_scheduler