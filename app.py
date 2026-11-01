
import os, re, uuid, json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY","")
if len(app.config["SECRET_KEY"])<32:
    raise RuntimeError("Set SECRET_KEY to a random secret of at least 32 characters")
db_url=os.getenv("DATABASE_URL")
if not db_url:
    if os.getenv("APP_ENV")=="production":
        raise RuntimeError("DATABASE_URL is required in production")
    db_url="sqlite:///brighton_dev.db"
if db_url.startswith("postgres://"):
    db_url="postgresql+psycopg://"+db_url[len("postgres://"):]
elif db_url.startswith("postgresql://"):
    db_url="postgresql+psycopg://"+db_url[len("postgresql://"):]
app.config["SQLALCHEMY_DATABASE_URI"]=db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
app.config["SESSION_COOKIE_HTTPONLY"]=True
app.config["SESSION_COOKIE_SAMESITE"]="Lax"
app.config["SESSION_COOKIE_SECURE"]=os.getenv("SESSION_COOKIE_SECURE","1")=="1"
app.config["PERMANENT_SESSION_LIFETIME"]=__import__("datetime").timedelta(hours=8)
app.config["MAX_CONTENT_LENGTH"]=10*1024*1024
db=SQLAlchemy(app)
csrf=CSRFProtect(app)
limiter=Limiter(get_remote_address,app=app,default_limits=["240 per hour"],storage_uri="memory://")
ROLES=["Admin","GM","PC","PM","CE","Site Engineer","Office Engineer","QS","Storekeeper","Procurement","Finance","General Foreman","Viewer"]
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)
    active=db.Column(db.Boolean,default=True,nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Project(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(30),unique=True,nullable=False)
    name=db.Column(db.String(200),nullable=False)
    project_type=db.Column(db.String(100),nullable=False)
    location=db.Column(db.String(250),nullable=False)
    city=db.Column(db.String(100),nullable=False)
    country=db.Column(db.String(100),nullable=False,default="Ethiopia")
    owner=db.Column(db.String(200),nullable=False)
    buildings=db.Column(db.Integer,nullable=False)
    basements=db.Column(db.Integer,nullable=False)
    upper_floors=db.Column(db.Integer,nullable=False)
    planned_start=db.Column(db.Date,nullable=False)
    planned_finish=db.Column(db.Date,nullable=False)
    currency=db.Column(db.String(3),nullable=False,default="ETB")
    status=db.Column(db.String(40),nullable=False,default="Draft")
    created_by=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Assignment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    project_id=db.Column(db.Integer,db.ForeignKey("project.id"),nullable=True)
    role=db.Column(db.String(50),nullable=False)
    reports_to_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    active=db.Column(db.Boolean,nullable=False,default=True)
    __table_args__=(db.UniqueConstraint("user_id","project_id","role",name="uq_assignment"),)
class Audit(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    actor_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    action=db.Column(db.String(100),nullable=False)
    entity=db.Column(db.String(40),nullable=False)
    entity_id=db.Column(db.Integer,nullable=False)
    details=db.Column(db.Text,nullable=False,default="{}")
    created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
def audit(action,entity,entity_id,details=None):
    db.session.add(Audit(actor_id=session["uid"],action=action,entity=entity,entity_id=entity_id,details=json.dumps(details or {})))
def me(): return db.session.get(User,session.get("uid")) if session.get("uid") else None
def roles(project_id=None):
    u=me()
    if not u:return set()
    rows=Assignment.query.filter_by(user_id=u.id,active=True).all()
    return {a.role for a in rows if a.project_id is None or a.project_id==project_id}
def require_login(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not me() or not me().active:
            session.clear()
            return redirect(url_for("login"))
        return fn(*a,**kw)
    return wrapped
def authorized(allowed,project_id=None):
    if not roles(project_id).intersection(allowed):abort(403)
def can_view(p):
    return bool(roles(p.id)) or p.created_by==session.get("uid")
@app.context_processor
def inject():return {"current_user":me(),"user_roles":roles(),"csrf_token":__import__("flask_wtf.csrf",fromlist=["generate_csrf"]).generate_csrf}
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Content-Security-Policy"]="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'"
    if request.is_secure:response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"]="no-store"
    return response
@app.route("/")
@require_login
def index():
    ps=[p for p in Project.query.order_by(Project.created_at.desc()).all() if can_view(p)]
    return render_template("index.html",projects=ps)
@app.route("/login",methods=["GET","POST"])
@limiter.limit("10 per minute")
def login():
    if request.method=="POST":
        u=User.query.filter_by(username=request.form.get("username","").strip().lower()).first()
        if u and u.active and check_password_hash(u.password_hash,request.form.get("password","")):
            session.clear();session["uid"]=u.id;session.permanent=True
            return redirect(url_for("index"))
        flash("Invalid credentials","error")
    return render_template("login.html")
@app.route("/logout",methods=["POST"])
@require_login
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/projects/new",methods=["GET","POST"])
@require_login
def new_project():
    authorized({"Admin","PC","PM"})
    if request.method=="POST":
        action=request.form.get("action")
        fields={k:request.form.get(k,"").strip() for k in ("code","name","project_type","location","city","country","owner","buildings","basements","upper_floors","planned_start","planned_finish","currency")}
        errors=[]
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,30}",fields["code"]):errors.append("Code must be 3–30 letters, numbers, hyphens or underscores.")
        for k in ("name","project_type","location","city","country","owner"):
            if not fields[k]:errors.append(f"{k.replace('_',' ').title()} is required.")
        try:
            buildings=int(fields["buildings"]);basements=int(fields["basements"]);upper=int(fields["upper_floors"])
            if buildings<1 or basements<0 or upper<1:raise ValueError()
        except ValueError:errors.append("Buildings must be at least 1, basements at least 0, and upper floors at least 1.");buildings=basements=upper=0
        try:
            start=__import__("datetime").date.fromisoformat(fields["planned_start"]);finish=__import__("datetime").date.fromisoformat(fields["planned_finish"])
            if finish<=start:errors.append("Planned completion must be after planned start.")
        except ValueError:errors.append("Valid planned start and completion dates are required.");start=finish=None
        if fields["currency"] not in ("ETB","USD","EUR"):errors.append("Select a supported currency.")
        if Project.query.filter_by(code=fields["code"]).first():errors.append("Project code already exists.")
        if not errors:
            p=Project(**{k:fields[k] for k in ("code","name","project_type","location","city","country","owner","currency")},buildings=buildings,basements=basements,upper_floors=upper,planned_start=start,planned_finish=finish,created_by=session["uid"])
            db.session.add(p);db.session.flush()
            audit("project_created","project",p.id,{"status":"Draft"})
            if action=="submit":
                p.status="Pending Approval"
                audit("project_submitted","project",p.id,{"status":"Pending Approval"})
            db.session.commit()
            flash("Project saved as "+p.status+".","success")
            return redirect(url_for("project_detail",pid=p.id))
        for e in errors:flash(e,"error")
    return render_template("project_form.html")
@app.route("/projects/<int:pid>")
@require_login
def project_detail(pid):
    p=db.get_or_404(Project,pid)
    if not can_view(p):abort(403)
    events=Audit.query.filter_by(entity="project",entity_id=pid).order_by(Audit.id.desc()).all()
    return render_template("project_detail.html",p=p,events=events,can_submit=bool(roles(pid)&{"Admin","PC","PM"}),can_approve=bool(roles(pid)&{"GM","PC"}))
@app.route("/projects/<int:pid>/transition",methods=["POST"])
@require_login
def transition(pid):
    p=db.get_or_404(Project,pid)
    action=request.form.get("action")
    rules={"submit":("Draft","Pending Approval",{"Admin","PC","PM"}),"approve":("Pending Approval","Approved",{"GM","PC"}),"return":("Pending Approval","Returned",{"GM","PC"}),"resubmit":("Returned","Pending Approval",{"Admin","PC","PM"}),"activate":("Approved","Active",{"PC","PM"})}
    if action not in rules:abort(400)
    old,new,allowed=rules[action]
    authorized(allowed,pid)
    if p.status!=old:abort(409)
    if action=="approve" and p.created_by==session["uid"]:
        abort(403,description="Project creator cannot approve their own project.")
    reason=request.form.get("reason","").strip()
    if action=="return" and not reason:abort(400)
    p.status=new;audit("project_"+action,"project",p.id,{"from":old,"to":new,"reason":reason});db.session.commit()
    flash("Project status: "+new,"success")
    return redirect(url_for("project_detail",pid=pid))
@app.route("/users",methods=["GET","POST"])
@require_login
def users():
    authorized({"Admin"})
    if request.method=="POST":
        name=request.form.get("username","").strip().lower()
        pw=request.form.get("password","")
        role=request.form.get("role","")
        if not re.fullmatch(r"[a-z0-9._-]{3,80}",name) or len(pw)<12 or role not in ROLES or User.query.filter_by(username=name).first():
            flash("Use a unique username, a password of at least 12 characters, and a valid role.","error")
        else:
            u=User(username=name,password_hash=generate_password_hash(pw));db.session.add(u);db.session.flush()
            db.session.add(Assignment(user_id=u.id,role=role,project_id=None))
            audit("user_created","user",u.id,{"role":role})
            db.session.commit();flash("User created.","success")
    all_users=User.query.order_by(User.username).all()
    return render_template("users.html",users=all_users,role_options=ROLES)
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables initialized. Use create-admin to set up the first account.")
@app.cli.command("create-admin")
def create_admin():
    import getpass
    username=input("Admin username: ").strip().lower()
    pw=getpass.getpass("Admin password (at least 12 chars): ")
    if len(pw)<12 or not re.fullmatch(r"[a-z0-9._-]{3,80}",username):raise ValueError("Invalid username/password")
    if User.query.filter_by(username=username).first():raise ValueError("Username exists")
    u=User(username=username,password_hash=generate_password_hash(pw))
    db.session.add(u);db.session.flush();db.session.add(Assignment(user_id=u.id,role="Admin"));db.session.commit()
    print("Admin created.")

@app.get("/health")
def health():
    return {"status":"ok"},200
