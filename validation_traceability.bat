@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "OUT=%~dp0validation_traceability_results.txt"

echo ================================================ > "%OUT%"
echo TRACEABILITY VALIDATION RESULTS >> "%OUT%"
echo Date: %date% %time% >> "%OUT%"
echo ================================================ >> "%OUT%"
echo. >> "%OUT%"

echo [1/5] Database record counts...
echo [1/5] Database record counts... >> "%OUT%"
"%PYTHON%" -c "from app.db.database import SessionLocal; from app.db import models; db=SessionLocal(); print('NCRs:',db.query(models.NCR).count()); print('Serial Units:',db.query(models.SerialUnit).count()); print('Lots:',db.query(models.Lot).count()); print('Manufacturing Orders:',db.query(models.ManufacturingOrder).count()); print('Products:',db.query(models.Product).count()); db.close()" >> "%OUT%" 2>&1

echo [2/5] Valid NCR traceability...
echo [2/5] Valid NCR traceability... >> "%OUT%"
"%PYTHON%" -c "from app.db.database import SessionLocal; from app.agents.traceability_agent import ProductTraceabilityAgent; from app.agents.models import InvestigationRequest; db=SessionLocal(); r=ProductTraceabilityAgent().run(db, InvestigationRequest(ncr_number='NCR-20260001')); print(r.model_dump_json(indent=2)); db.close()" >> "%OUT%" 2>&1

echo [3/5] Nonexistent NCR fail-closed test...
echo [3/5] Nonexistent NCR fail-closed test... >> "%OUT%"
"%PYTHON%" -c "from app.db.database import SessionLocal; from app.agents.traceability_agent import ProductTraceabilityAgent; from app.agents.models import InvestigationRequest; db=SessionLocal(); r=ProductTraceabilityAgent().run(db, InvestigationRequest(ncr_number='NCR-999999')); print(r.model_dump_json(indent=2)); db.close()" >> "%OUT%" 2>&1

echo [4/5] Empty NCR validation...
echo [4/5] Empty NCR validation... >> "%OUT%"
"%PYTHON%" -c "from app.db.database import SessionLocal; from app.agents.traceability_agent import ProductTraceabilityAgent; from app.agents.models import InvestigationRequest; db=SessionLocal(); r=ProductTraceabilityAgent().run(db, InvestigationRequest(ncr_number='')); print(r.model_dump_json(indent=2)); db.close()" >> "%OUT%" 2>&1

echo [5/5] Direct NCR genealogy data...
echo [5/5] Direct NCR genealogy data... >> "%OUT%"
"%PYTHON%" -c "from app.db.database import SessionLocal; from app.db import models; db=SessionLocal(); n=db.query(models.NCR).filter(models.NCR.ncr_number=='NCR-20260001').first(); print('NCR:',n.ncr_number if n else None); print('NCR ID:',n.id if n else None); print('NCR object:',n.__dict__ if n else None); db.close()" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo ================================================ >> "%OUT%"
echo TRACEABILITY VALIDATION COMPLETE >> "%OUT%"
echo ================================================ >> "%OUT%"

type "%OUT%"
pause
