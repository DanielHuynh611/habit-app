(() => {
'use strict';
const config={"actions":[{"authentication":"required","function_id":"capability_calendar_heatmap_visualization_28ed1af0.function.get_habit_heatmap_data","id":"capability_calendar_heatmap_visualization_28ed1af0.screen-action.load_heatmap_data","method":"GET","request_schema":{"properties":{"end_date":{"description":"ISO 8601 date string for the end of the heatmap range (defaults to today)","format":"date","location":"query","required":false,"type":"string"},"habit_id":{"description":"The unique identifier of the habit to visualize","location":"path","type":"string"},"start_date":{"description":"ISO 8601 date string for the beginning of the heatmap range (defaults to several weeks ago)","format":"date","location":"query","required":false,"type":"string"}},"required":["habit_id"],"type":"object"},"response_schema":{"properties":{"completion_rate":{"description":"Percentage of days completed out of total days in range (0.0 to 100.0)","format":"float","maximum":100,"minimum":0,"type":"number"},"current_streak":{"description":"The number of consecutive days (up to today) the habit has been completed","minimum":0,"type":"integer"},"days":{"description":"Array of day objects covering the date range, each indicating completion status","items":{"properties":{"completed":{"description":"True if the habit was marked complete on this date, false otherwise","type":"boolean"},"date":{"description":"ISO 8601 date string for this calendar cell","format":"date","type":"string"},"is_future":{"description":"True if this date is in the future relative to today","type":"boolean"}},"required":["date","completed","is_future"],"type":"object"},"type":"array"},"end_date":{"description":"The actual end date of the returned data range","format":"date","type":"string"},"habit_id":{"description":"The habit identifier","type":"string"},"habit_name":{"description":"The name of the habit for display context","type":"string"},"start_date":{"description":"The actual start date of the returned data range","format":"date","type":"string"}},"required":["habit_id","habit_name","start_date","end_date","days","current_streak","completion_rate"],"type":"object"},"route":"/api/habits/:habit_id/heatmap","success_route":null},{"authentication":"required","function_id":"capability_calendar_heatmap_visualization_28ed1af0.function.get_habit_heatmap_data","id":"capability_calendar_heatmap_visualization_28ed1af0.screen-action.refresh_heatmap_after_completion","method":"GET","request_schema":{"properties":{"end_date":{"description":"ISO 8601 date string for the end of the heatmap range (defaults to today)","format":"date","location":"query","required":false,"type":"string"},"habit_id":{"description":"The unique identifier of the habit to visualize","location":"path","type":"string"},"start_date":{"description":"ISO 8601 date string for the beginning of the heatmap range (defaults to several weeks ago)","format":"date","location":"query","required":false,"type":"string"}},"required":["habit_id"],"type":"object"},"response_schema":{"properties":{"completion_rate":{"description":"Percentage of days completed out of total days in range (0.0 to 100.0)","format":"float","maximum":100,"minimum":0,"type":"number"},"current_streak":{"description":"The number of consecutive days (up to today) the habit has been completed","minimum":0,"type":"integer"},"days":{"description":"Array of day objects covering the date range, each indicating completion status","items":{"properties":{"completed":{"description":"True if the habit was marked complete on this date, false otherwise","type":"boolean"},"date":{"description":"ISO 8601 date string for this calendar cell","format":"date","type":"string"},"is_future":{"description":"True if this date is in the future relative to today","type":"boolean"}},"required":["date","completed","is_future"],"type":"object"},"type":"array"},"end_date":{"description":"The actual end date of the returned data range","format":"date","type":"string"},"habit_id":{"description":"The habit identifier","type":"string"},"habit_name":{"description":"The name of the habit for display context","type":"string"},"start_date":{"description":"The actual start date of the returned data range","format":"date","type":"string"}},"required":["habit_id","habit_name","start_date","end_date","days","current_streak","completion_rate"],"type":"object"},"route":"/api/habits/:habit_id/heatmap","success_route":null}],"screen_route":"/habits/:habit_id/heatmap"};
const actionById=new Map(config.actions.map(action=>[action.id,action]));
const routeNames=template=>[...String(template||'').matchAll(/\{([A-Za-z_]\w*)\}/g)].map(match=>match[1]);
const previewValue=name=>name.endsWith('_id')||name==='id'?'example-id':'example';
const routeValues=()=>{
  const names=routeNames(config.screen_route);
  const pattern='^'+String(config.screen_route||'/').replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\\\{([A-Za-z_]\w*)\\\}/g,'([^/]+)')+'$';
  const match=location.pathname.match(new RegExp(pattern));
  return Object.fromEntries(names.map((name,index)=>[name,match?decodeURIComponent(match[index+1]||''):previewValue(name)]));
};
const materialize=(template,values)=>String(template||'').replace(/\{([A-Za-z_]\w*)\}/g,(_,name)=>encodeURIComponent(values[name]??previewValue(name)));
const valueAt=(value,path)=>String(path||'').split('.').reduce((current,key)=>current&&typeof current==='object'?current[key]:undefined,value);
const display=value=>value==null?'—':typeof value==='object'?JSON.stringify(value):String(value);
const render=(payload,scope=document)=>scope.querySelectorAll('[data-bind]').forEach(node=>{
  const value=valueAt(payload,node.dataset.bind);
  if(value===undefined)return;
  if(Array.isArray(value)){
    const template=node.firstElementChild?.cloneNode(true);node.replaceChildren();
    value.forEach(item=>{if(template){const child=template.cloneNode(true);render(item,child);node.append(child);}else{const child=document.createElement('div');child.className='generated-item';child.textContent=display(item);node.append(child);}});
  }else node.textContent=display(value);
});
const region=(root,name)=>root.querySelector(`[data-${name}-region]`)||document.querySelector(`[data-${name}-region]`);
const show=(root,name,message)=>{const target=region(root,name);if(target){target.hidden=false;if(message)target.textContent=message;}};
const loading=(root,value)=>{root.dataset.loading=String(Boolean(value));root.querySelectorAll('button,input,textarea,select').forEach(node=>node.disabled=Boolean(value));};
const valuesFrom=root=>{const form=root.tagName==='FORM'?root:root.querySelector('form');return form?Object.fromEntries(new FormData(form).entries()):{};};
const coerce=(values,schema)=>Object.fromEntries(Object.entries(values).map(([key,value])=>{const rules=schema?.properties?.[key]||{};if(rules.type==='integer')return[key,Number.parseInt(value,10)];if(rules.type==='number')return[key,Number(value)];if(rules.type==='boolean')return[key,['true','1','on','yes'].includes(String(value).toLowerCase())];return[key,value];}));
const execute=async(root,action)=>{
  const requestSchema=action.request_schema||{};const requestValues=coerce(valuesFrom(root),requestSchema);const values={...routeValues(),...requestValues};let url=materialize(action.route,values);
  for(const name of requestSchema.required||[]){if(requestValues[name]===''||requestValues[name]===undefined){show(root,'error',`${name.replaceAll('_',' ')} is required.`);return;}}
  const pathNames=new Set(routeNames(action.route));const allowed=new Set(Object.keys(requestSchema.properties||{}));const body=Object.fromEntries(Object.entries(requestValues).filter(([key,value])=>allowed.has(key)&&!pathNames.has(key)&&value!==''));
  const headers={Accept:'application/json'};const token=localStorage.getItem('zorentia_access_token');if(action.authentication==='required'&&!token&&!window.__ZORENTIA_PREVIEW__){show(root,'error','Please sign in before using this action.');return;}if(token)headers.Authorization=`Bearer ${token}`;
  const options={method:action.method,headers};
  if(['GET','HEAD'].includes(action.method)){const query=new URLSearchParams(Object.entries(body));if(query.size)url+=`${url.includes('?')?'&':'?'}${query}`;}
  else{headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
  loading(root,true);const errorRegion=region(root,'error');if(errorRegion)errorRegion.hidden=true;
  try{const response=await fetch(url,options);const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(payload.message||payload.error||`Request failed (${response.status})`);if(payload.token)localStorage.setItem('zorentia_access_token',payload.token);render(payload,root);show(root,'success');if(action.success_route&&!window.__ZORENTIA_PREVIEW__)location.href=materialize(action.success_route,{...values,...payload});}
  catch(error){show(root,'error',error?.message||'Something went wrong. Please try again.');}
  finally{loading(root,false);}
};
document.querySelectorAll('[data-action-id]').forEach(root=>{
  const action=actionById.get(root.dataset.actionId);if(!action)return;
  if(root.tagName==='FORM')root.addEventListener('submit',event=>{event.preventDefault();execute(root,action);});
  else root.addEventListener('click',event=>{if(event.target.closest('button,[data-trigger]'))execute(root,action);});
  if(['GET','HEAD'].includes(action.method)&&root.dataset.autoload==='true')execute(root,action);
});
})();

(function() {
  const container = document.getElementById('heatmap-grid');
  if (!container) return;

  function renderHeatmap(data) {
    if (!data || !data.days || data.days.length === 0) {
      container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #607370;">No data available</div>';
      return;
    }

    const days = data.days;
    const weeks = [];
    let currentWeek = [];

    // Parse dates and organize into weeks
    const startDate = new Date(days[0].date);
    const startDay = startDate.getDay(); // 0 = Sunday

    // Add empty cells for the first week if it doesn't start on Sunday
    for (let i = 0; i < startDay; i++) {
      currentWeek.push(null);
    }

    days.forEach(day => {
      currentWeek.push(day);
      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    });

    // Add remaining days to last week
    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      weeks.push(currentWeek);
    }

    // Build the grid HTML
    let html = '<div style="display: flex; gap: 0.25rem;">';
    
    // Day labels column
    html += '<div style="display: flex; flex-direction: column; gap: 0.25rem; padding-right: 0.5rem; font-size: 0.75rem; color: #607370; justify-content: space-around;">';
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayLabels.forEach(label => {
      html += `<div style="height: 16px; line-height: 16px;">${label}</div>`;
    });
    html += '</div>';

    // Calendar grid
    html += '<div style="flex: 1;">';
    
    // Month labels
    html += '<div style="display: flex; gap: 0.25rem; margin-bottom: 0.5rem; font-size: 0.75rem; color: #607370; font-weight: 500;">';
    const monthsShown = new Set();
    weeks.forEach((week, weekIndex) => {
      const firstDay = week.find(d => d !== null);
      if (firstDay) {
        const date = new Date(firstDay.date);
        const monthName = date.toLocaleDateString('en-US', { month: 'short' });
        const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
        
        if (!monthsShown.has(monthKey) && (weekIndex === 0 || date.getDate() <= 7)) {
          html += `<div style="width: 16px; text-align: center;">${monthName}</div>`;
          monthsShown.add(monthKey);
        } else {
          html += '<div style="width: 16px;"></div>';
        }
      } else {
        html += '<div style="width: 16px;"></div>';
      }
    });
    html += '</div>';

    // Week columns
    html += '<div style="display: flex; gap: 0.25rem;">';
    weeks.forEach(week => {
      html += '<div style="display: flex; flex-direction: column; gap: 0.25rem;">';
      week.forEach(day => {
        if (day === null) {
          html += '<div style="width: 16px; height: 16px;"></div>';
        } else {
          let bgColor = '#E5E7EB';
          let borderStyle = '';
          let title = new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
          
          if (day.is_future) {
            bgColor = '#F9FAFB';
            borderStyle = 'border: 1px solid #E5E7EB;';
            title += ' (Future)';
          } else if (day.completed) {
            bgColor = '#10B981';
            title += ' - Completed';
          } else {
            title += ' - Missed';
          }
          
          html += `<div style="width: 16px; height: 16px; background: ${bgColor}; border-radius: 4px; ${borderStyle} cursor: pointer; transition: transform 0.1s;" title="${title}" onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'"></div>`;
        }
      });
      html += '</div>';
    });
    html += '</div>';
    
    html += '</div>';
    html += '</div>';

    container.innerHTML = html;
  }

  // Listen for data updates
  document.addEventListener('action:success', function(e) {
    if (e.detail && e.detail.actionId === 'capability_calendar_heatmap_visualization_28ed1af0.screen-action.load_heatmap_data') {
      renderHeatmap(e.detail.data);
    }
    if (e.detail && e.detail.actionId === 'capability_calendar_heatmap_visualization_28ed1af0.screen-action.refresh_heatmap_after_completion') {
      renderHeatmap(e.detail.data);
    }
  });
})();