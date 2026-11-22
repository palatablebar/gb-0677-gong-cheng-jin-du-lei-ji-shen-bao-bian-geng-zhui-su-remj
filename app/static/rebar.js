const notice=document.getElementById('notice');
function call(path,data){
  notice.textContent='处理中…';
  return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    .then(async response=>{const body=await response.json();if(!response.ok)throw new Error(body.message);window.location.reload();})
    .catch(error=>{notice.textContent=error.message;});
}
document.getElementById('calculate').addEventListener('click',function(){
  call('/api/rebar/runs',{sample:document.getElementById('dataset').value});
});
document.getElementById('approve').addEventListener('click',function(){
  call('/api/rebar/runs/'+certificate.id+'/review',{version:certificate.version,decision:'已复核'});
});
document.getElementById('publish').addEventListener('click',function(){
  call('/api/rebar/runs/'+certificate.id+'/publish',{version:certificate.version});
});
document.getElementById('publish-fail').addEventListener('click',function(){
  notice.textContent='演练发布失败，验证回滚…';
  fetch('/api/rebar/runs/'+certificate.id+'/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:certificate.version,simulate_failure:true})})
    .then(async response=>{const body=await response.json();notice.textContent=response.ok?'异常：演练未失败':('已恢复旧版：'+body.message);})
    .catch(error=>notice.textContent=error.message);
});
document.getElementById('attach').addEventListener('click',async()=>{
  const file=document.getElementById('attachment').files[0];
  if(!file){notice.textContent='请选择领料文件。';return;}
  notice.textContent='导入中…';
  const form=new FormData();form.append('file',file);
  try{
    const response=await fetch('/api/rebar/upload',{method:'POST',body:form});
    const body=await response.json();
    if(!response.ok)throw new Error(body.message);
    location.reload();
  }catch(error){notice.textContent=error.message;}
});
document.getElementById('lookup')?.addEventListener('input',function(){
  document.querySelectorAll('#valuation-rows tr').forEach(row=>row.hidden=!row.textContent.includes(this.value));
});
