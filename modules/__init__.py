#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modules 패키지 초기화
각 독립 모듈들의 컨테이너 역할
"""

__version__ = '1.0.0'

# 이 파일은 modules 패키지를 Python 패키지로 인식시키는 역할만 합니다.
# 실제 모듈 등록은 각 하위 모듈의 register_module 함수를 통해 이루어집니다.

# 사용 가능한 모듈 목록
AVAILABLE_MODULES = [
    'top_rate_analysi',  # 등락율상위분석
    # 'stock_setting',    # 종목설정 (추후 추가)
    # 'ai_analysis',      # AI분석 (추후 추가)
    # 'chart_analysis',   # 차트분석 (추후 추가)
]


def get_available_modules():
    """사용 가능한 모듈 목록 반환"""
    return AVAILABLE_MODULES


def register_all_modules(app):
    """모든 사용 가능한 모듈을 앱에 등록"""
    registered_count = 0

    for module_name in AVAILABLE_MODULES:
        try:
            # 동적 import
            module = __import__(f'modules.{module_name}', fromlist=['register_module'])
            if hasattr(module, 'register_module'):
                success = module.register_module(app)
                if success:
                    registered_count += 1
                    app.logger.info(f"✅ {module_name} 모듈 등록 완료")
                else:
                    app.logger.warning(f"⚠️ {module_name} 모듈 등록 실패")
            else:
                app.logger.warning(f"⚠️ {module_name} 모듈에 register_module 함수가 없습니다")

        except ImportError as e:
            app.logger.warning(f"⚠️ {module_name} 모듈을 찾을 수 없습니다: {e}")
        except Exception as e:
            app.logger.error(f"❌ {module_name} 모듈 등록 중 오류: {e}")

    app.logger.info(f"📦 총 {registered_count}/{len(AVAILABLE_MODULES)}개 모듈 등록 완료")
    return registered_count