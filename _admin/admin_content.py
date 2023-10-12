from dataclasses import dataclass
from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
from common import *


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
# templates.env.globals['getattr'] = getattr
# templates.env.globals['today'] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals["now"] = now
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_head_tail_img"] = get_head_tail_img
templates.env.globals["generate_one_time_token"] = generate_one_time_token


@router.get("/content_list")
def content_list(request: Request, db: Session = Depends(get_db)):
    """
    내용관리 목록
    """
    request.session["menu_key"] = "300600"

    contents = db.query(models.Content).all()
    return templates.TemplateResponse(
        "admin/content_list.html", {"request": request, "contents": contents}
    )


# 내용추가 폼
@router.get("/content_form")
def content_form_add(request: Request, db: Session = Depends(get_db)):

    return templates.TemplateResponse(
        "admin/content_form.html", {"request": request, "content": None}
    )


@dataclass
class ContentDataclass:
    """내용 등록/수정 폼 데이터
    """
    co_subject: str = Form(...)
    co_content: str = Form(None)
    co_mobile_content: str = Form(None)
    co_html: str = Form(None)
    co_skin: str = Form(None)
    co_mobile_skin: str = Form(None)


# 내용 등록 처리
@router.post("/content_form")
def content_add(
        request: Request,
        token: str = Form(...),
        co_id: str = Form(...),
        co_himg: UploadFile = File(None),
        co_timg: UploadFile = File(None),
        data: ContentDataclass = Depends(),
        db: Session = Depends(get_db)
    ):
    # 토큰 검사
    if not validate_one_time_token(token):
        raise HTTPException(status_code=403, detail="Invalid token.")
    # ID 중복 검사
    chk_content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
    if chk_content:
        raise HTTPException(status_code=404, detail=f"{co_id} : 내용아이디가 이미 존재합니다.")
    
    # 내용 등록
    content = models.Content(co_id=co_id, **data.__dict__)
    db.add(content)
    db.commit()

    # 이미지 경로 검사 및 생성
    image_directory = "data/content/"
    make_directory(image_directory)

    # 이미지 저장
    save_image(image_directory, f"{co_id}_h", co_himg)
    save_image(image_directory, f"{co_id}_t", co_timg)

    return RedirectResponse(url=f"/admin/content_form/{content.co_id}", status_code=302)


# 내용수정 폼
@router.get("/content_form/{co_id}")
def content_form_edit(co_id: str, request: Request, db: Session = Depends(get_db)):
    content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
    if not content:
        raise HTTPException(status_code=404, detail=f"{co_id} is not found.")

    return templates.TemplateResponse(
        "admin/content_form.html",
        {"request": request, "content": content},
    )


# 내용 수정 처리
@router.post("/content_form/{co_id}")
def content_edit(
    request: Request,
    co_id: str,
    token: str = Form(...),
    data: ContentDataclass = Depends(),
    co_himg: UploadFile = File(...),
    co_timg: UploadFile = File(...),
    co_himg_del: bool = Form(None),
    co_timg_del: bool = Form(None),
    db: Session = Depends(get_db),
):
    # 토큰 검사
    if not validate_one_time_token(token):
        raise HTTPException(status_code=403, detail="Invalid token.")
    # 내용 검사
    content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
    if not content:
        raise HTTPException(status_code=404, detail=f"{co_id} : 내용 아이디가 존재하지 않습니다.")

    # 데이터 수정 후 commit
    for field, value in data.__dict__.items():
        setattr(content, field, value)
    db.commit()

    # 이미지 경로체크 및 생성
    image_directory = "data/content/"
    make_directory(image_directory)

    # 이미지 삭제
    delete_image(image_directory, f"{co_id}_h", co_himg_del)
    delete_image(image_directory, f"{co_id}_t", co_timg_del)

    # 이미지 저장
    save_image(image_directory, f"{co_id}_h", co_himg)
    save_image(image_directory, f"{co_id}_t", co_timg)

    return RedirectResponse(url=f"/admin/content_form/{co_id}", status_code=302)


# DB등록 및 수정
# 사라지는 기능
# 1. 상단 파일 경로 (co_include_head)
# 2. 하단 파일 경로 (co_include_tail)
# TODO: Pydantic 모델 프로세스가 적용된다면 삭제예정
@router.post("/content_form_update")
def content_form_update(request: Request,
                        db: Session = Depends(get_db),
                        token: str = Form(...),
                        co_id: str = Form(...),
                        co_subject: str = Form(...),
                        co_content: str = Form(None),
                        co_mobile_content: str = Form(None),
                        co_html: str = Form(None),
                        co_skin: str = Form(None),
                        co_mobile_skin: str = Form(None),
                        # co_include_head: str = Form(None),
                        # co_include_tail: str = Form(None),
                        co_himg: UploadFile = File(...),
                        co_timg: UploadFile = File(...),
                        co_himg_del: int = Form(None),
                        co_timg_del: int = Form(None),
                        ):
    # 세션에 저장된 토큰값과 입력된 토큰값이 다르다면 에러 (토큰 변조시 에러)
    # 토큰은 외부에서 접근하는 것을 막고 등록, 수정을 구분하는 용도로 사용
    ss_token = request.session.get("token", "")
    if not token or token != ss_token:
        raise HTTPException(status_code=403, detail="Invalid token.")

    # 수정의 경우 토큰값이 회원아이디로 만들어지므로 토큰값이 회원아이디와 다르다면 등록으로 처리
    # 회원아이디 변조시에도 등록으로 처리
    if not verify_password(co_id, token):  # 등록
        chk_content = (
            db.query(models.Content).filter(models.Content.co_id == co_id).first()
        )
        if chk_content:
            raise HTTPException(status_code=404, detail=f"{co_id} : 내용아이디가 이미 존재합니다.")

        content = models.Content(
            co_id=co_id,
            co_subject=co_subject,
            co_content=co_content,
            co_mobile_content=co_mobile_content,
            co_html=co_html,
            co_skin=co_skin if co_skin else "",
            co_mobile_skin=co_mobile_skin if co_mobile_skin else "",
            # co_include_head=co_include_head if co_include_head else "",
            # co_include_tail=co_include_tail if co_include_tail else "",
        )
        db.add(content)
        db.commit()
        
    else:  # 수정
        content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
        if not content:
            raise HTTPException(status_code=404, detail=f"{co_id} : 내용아이디가 존재하지 않습니다.")

        content.co_subject = co_subject
        content.co_content = co_content
        content.co_mobile_content = co_mobile_content
        content.co_html = co_html
        content.co_skin = co_skin if co_skin else ""
        content.co_mobile_skin = co_mobile_skin if co_mobile_skin else ""
        # content.co_include_head = co_include_head if co_include_head else ""
        # content.co_include_tail = co_include_tail if co_include_tail else ""
        db.commit()
        
    # 이미지 삭제
    if co_himg_del:
        if os.path.exists(f"data/content/{co_id}_h"):
            os.remove(f"data/content/{co_id}_h")
        
    if co_timg_del:
        if os.path.exists(f"data/content/{co_id}_t"):
            os.remove(f"data/content/{co_id}_t")
    
    # 이미지 저장
    if co_himg and co_himg.filename:    
        with open(f"data/content/{co_id}_h", "wb") as buffer:
            shutil.copyfileobj(co_himg.file, buffer)
    
    if co_timg and co_timg.filename:    
        with open(f"data/content/{co_id}_t", "wb") as buffer:
            shutil.copyfileobj(co_timg.file, buffer)

    return RedirectResponse(url=f"/admin/content_form/{co_id}", status_code=302)


@router.get("/content_delete/{co_id}")
def content_delete(co_id: str, 
                   request: Request, 
                   db: Session = Depends(get_db),
                   token: str = Query(...),):
    if not validate_one_time_token(token):
        raise HTTPException(status_code=403, detail="Invalid token.")
    
    content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
    if not content:
        raise HTTPException(status_code=404, detail=f"{co_id} is not found.")

    # 이미지 삭제
    if os.path.exists(f"data/content/{co_id}_h"):
        os.remove(f"data/content/{co_id}_h")

    if os.path.exists(f"data/content/{co_id}_t"):
        os.remove(f"data/content/{co_id}_t")
        
    db.delete(content)
    db.commit()
    return RedirectResponse(url=f"/admin/content_list", status_code=302)
