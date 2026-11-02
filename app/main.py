from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlencode
import asyncio, time

from fastapi import FastAPI, Depends, HTTPException, Query, Header, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import settings
from .store import initialize_from_csv, load_manifest, query_resource, write_test, get_write, update_write, delete_write
from .auth import api_key, basic, static_bearer, local_oauth, entra, issue_local_token

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.row_counts = initialize_from_csv(reload=False)
    yield

app=FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Dataset-backed mock API platform for Azure Data Factory. Supports multiple sources, auth patterns, extraction/pagination styles, incremental filters, CRUD test endpoints and failure simulation.",
    lifespan=lifespan
)

class WritePayload(BaseModel):
    resource: str = Field(default="test-resource",max_length=100)
    data: dict = Field(default_factory=dict)

@app.get("/",tags=["Health"])
def root():
    return {"service":settings.app_name,"status":"running","docs":"/docs","openapi":"/openapi.json"}

@app.get("/health",tags=["Health"])
def health():
    return {"status":"healthy","source_count":len(load_manifest()["tables"]),
            "tables":app.state.row_counts,"total_records":sum(app.state.row_counts.values())}

@app.get("/api/metadata",tags=["Metadata"])
def metadata():
    return {"sources":[{"resource":x["resource"],"table":x["table"],"domain":x["domain"],"expected_rows":x["rows"],"columns":x["columns"]} for x in load_manifest()["tables"]]}

@app.post("/oauth/token",tags=["OAuth2"])
def oauth_token(
    grant_type: str=Form(...),
    client_id: str=Form(...),
    client_secret: str=Form(...)
):
    if grant_type!="client_credentials":
        raise HTTPException(400,"Only client_credentials grant is supported")
    token=issue_local_token(client_id,client_secret)
    return {"access_token":token,"token_type":"Bearer","expires_in":settings.oauth_token_ttl_seconds,"scope":"Data.Read Data.Write"}

AUTH_MODES={
    "apikey":(api_key,"api-key"),
    "basic":(basic,"basic"),
    "bearer":(static_bearer,"static-bearer"),
    "oauth":(local_oauth,"local-oauth2"),
    "entra":(entra,"microsoft-entra-id")
}

def make_resource_handler(prefix, dependency, auth_label):
    async def handler(
        resource: str,
        request: Request,
        page: int=Query(1,ge=1),
        page_size: int=Query(settings.default_page_size,ge=1,le=settings.max_page_size),
        offset: Optional[int]=Query(None,ge=0),
        limit: Optional[int]=Query(None,ge=1,le=settings.max_page_size),
        pagination: str=Query("page",pattern="^(page|offset|none)$"),
        response_format: str=Query("envelope",pattern="^(envelope|array|odata)$"),
        vendor_code: Optional[str]=None,
        employee_email: Optional[str]=None,
        ticket_number: Optional[str]=None,
        approval_status: Optional[str]=None,
        submission_status: Optional[str]=None,
        activity_type: Optional[str]=None,
        status: Optional[str]=None,
        product_code: Optional[str]=None,
        article_code: Optional[str]=None,
        date_from: Optional[str]=None,
        date_to: Optional[str]=None,
        modified_since: Optional[str]=None,
        order_by: Optional[str]=None,
        auth=Depends(dependency)
    ):
        filters={k:v for k,v in {
            "VendorCode":vendor_code,"EmployeeEmail":employee_email,"TicketNumber":ticket_number,
            "ApprovalStatus":approval_status,"SubmissionStatus":submission_status,
            "ActivityType":activity_type,"Status":status,"ProductCode":product_code,
            "ArticleCode":article_code
        }.items() if v is not None}
        if pagination=="none":
            actual_limit=settings.max_page_size
            actual_offset=0
        elif pagination=="offset":
            actual_limit=limit or page_size
            actual_offset=offset or 0
        else:
            actual_limit=page_size
            actual_offset=(page-1)*page_size
        try:
            total,rows,columns=query_resource(resource,actual_limit,actual_offset,filters,date_from,date_to,modified_since,order_by)
        except KeyError:
            raise HTTPException(404,detail=f"Unknown resource '{resource}'. See /api/metadata.")
        except ValueError as e:
            raise HTTPException(400,detail=str(e))
        has_more=actual_offset+len(rows)<total
        next_page=(page+1 if has_more and pagination=="page" else None)
        next_offset=(actual_offset+len(rows) if has_more and pagination=="offset" else None)
        base=str(request.url).split("?")[0]
        next_link=None
        if has_more and pagination!="none":
            params=dict(request.query_params)
            if pagination=="offset":
                params["offset"]=str(next_offset)
                params["limit"]=str(actual_limit)
            else:
                params["page"]=str(next_page)
                params["page_size"]=str(actual_limit)
            next_link=base+"?"+urlencode(params)
        if response_format=="array":
            return rows
        if response_format=="odata":
            return {"@odata.count":total,"value":rows,"@odata.nextLink":next_link}
        return {
            "resource":resource,"authentication":auth_label,
            "page":page if pagination=="page" else None,
            "offset":actual_offset,"page_size":actual_limit,
            "total_records":total,"returned_records":len(rows),
            "has_more":has_more,"next_page":next_page,
            "next_offset":next_offset,"next":next_link,
            "data":rows
        }
    app.add_api_route(f"{prefix}/{{resource}}",handler,methods=["GET"],tags=[f"Extract - {auth_label}"],name=f"{auth_label}_extract")

    async def post_handler(payload:WritePayload,auth=Depends(dependency)):
        wid=write_test(payload.resource, payload.data)
        return {"id":wid,"resource":payload.resource,"data":payload.data,"operation":"POST"}
    async def get_handler(write_id:int,auth=Depends(dependency)):
        record=get_write(write_id)
        if not record: raise HTTPException(404,"Write test record not found")
        return record
    async def put_handler(write_id:int,payload:WritePayload,auth=Depends(dependency)):
        rec=update_write(write_id,{"resource":payload.resource,"data":payload.data},replace=True)
        if not rec: raise HTTPException(404,"Write test record not found")
        return rec
    async def patch_handler(write_id:int,payload:dict,auth=Depends(dependency)):
        rec=update_write(write_id,payload,replace=False)
        if not rec: raise HTTPException(404,"Write test record not found")
        return rec
    async def delete_handler(write_id:int,auth=Depends(dependency)):
        if not delete_write(write_id): raise HTTPException(404,"Write test record not found")
        return {"deleted":True,"id":write_id}
    app.add_api_route(f"{prefix}/write-test",post_handler,methods=["POST"],tags=[f"Write - {auth_label}"])
    app.add_api_route(f"{prefix}/write-test/{{write_id}}",get_handler,methods=["GET"],tags=[f"Write - {auth_label}"])
    app.add_api_route(f"{prefix}/write-test/{{write_id}}",put_handler,methods=["PUT"],tags=[f"Write - {auth_label}"])
    app.add_api_route(f"{prefix}/write-test/{{write_id}}",patch_handler,methods=["PATCH"],tags=[f"Write - {auth_label}"])
    app.add_api_route(f"{prefix}/write-test/{{write_id}}",delete_handler,methods=["DELETE"],tags=[f"Write - {auth_label}"])

for mode,(dep,label) in AUTH_MODES.items():
    make_resource_handler(f"/api/{mode}",dep,label)

@app.get("/api/errors/{status_code}",tags=["ADF Resilience Tests"])
def errors(status_code:int,x_api_key:Optional[str]=Header(default=None)):
    if x_api_key!=settings.api_key: raise HTTPException(401,"API key required")
    allowed={400,401,403,404,408,409,429,500,502,503,504}
    if status_code not in allowed: raise HTTPException(400,f"Allowed: {sorted(allowed)}")
    headers={"Retry-After":"15"} if status_code==429 else {}
    return JSONResponse(status_code=status_code,content={"error":f"Simulated HTTP {status_code}","scenario":"ADF retry/branch test"},headers=headers)

@app.get("/api/delay/{seconds}",tags=["ADF Resilience Tests"])
async def delay(seconds:int,x_api_key:Optional[str]=Header(default=None)):
    if x_api_key!=settings.api_key: raise HTTPException(401,"API key required")
    if seconds<0 or seconds>settings.max_delay_seconds: raise HTTPException(400,"Delay outside configured range")
    await asyncio.sleep(seconds)
    return {"status":"completed","delay_seconds":seconds}

@app.get("/api/stream/{resource}",tags=["Extraction Modes"])
async def stream(resource:str,request:Request,chunk_size:int=Query(1000,ge=1,le=10000),
                 x_api_key:Optional[str]=Header(default=None)):
    if x_api_key!=settings.api_key: raise HTTPException(401,"API key required")
    try:
        total,rows,cols=query_resource(resource,chunk_size,0)
    except KeyError: raise HTTPException(404,"Unknown resource")
    return {"resource":resource,"chunk_size":chunk_size,"total_records":total,"data":rows,
            "note":"Use pagination for subsequent chunks; this endpoint returns the first chunk."}
