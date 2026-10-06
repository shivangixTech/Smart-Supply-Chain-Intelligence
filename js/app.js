(() => {
'use strict';
const D = window.FMCG_DATA;
const CUBE_DATA = window.FMCG_CUBE || [];
const CUBE = Array.isArray(CUBE_DATA) ? CUBE_DATA : CUBE_DATA.rows;
const CUBE_COLUMNS = Array.isArray(CUBE_DATA) ? ['year','brand','category','region','channel','promotion_flag','records','revenue','units','stock','delivered','delivery_sum'] : CUBE_DATA.columns;
const CUBE_INDEX = Object.fromEntries(CUBE_COLUMNS.map((key,index)=>[key,index]));
const cubeValue = (row,key) => Array.isArray(row) ? row[CUBE_INDEX[key]] : row[key];
const SAMPLE = window.FMCG_SAMPLE || [];
const $ = (s, p=document) => p.querySelector(s);
const $$ = (s, p=document) => [...p.querySelectorAll(s)];
const NS='http://www.w3.org/2000/svg';
const colors={gold:'#d8b36a',goldSoft:'#e8c982',bronze:'#a67c52',emerald:'#6d9b74',amber:'#c9913e',coral:'#c66b5d',cream:'#d9cfc0',brown:'#5a4635',muted:'#beb4a5'};
const fmt={
  num:n=>new Intl.NumberFormat('en-IN',{maximumFractionDigits:0}).format(n||0),
  one:n=>new Intl.NumberFormat('en-IN',{minimumFractionDigits:1,maximumFractionDigits:1}).format(n||0),
  two:n=>new Intl.NumberFormat('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n||0),
  cr:n=>`₹${((n||0)/1e7).toFixed(2)} Cr`,
  mil:n=>`${((n||0)/1e6).toFixed(2)} M`,
  pct:n=>`${(n||0).toFixed(2)}%`,
  compact:n=>new Intl.NumberFormat('en-IN',{notation:'compact',maximumFractionDigits:1}).format(n||0)
};
const escapeHTML = v => String(v ?? '').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
function toast(msg){const el=$('#toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(toast.t); toast.t=setTimeout(()=>el.classList.remove('show'),2200)}
function svgEl(tag,attrs={}){const el=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));return el}
function clear(el){el.innerHTML=''}
function scaleLinear(v,min,max,outMin,outMax){if(max===min)return (outMin+outMax)/2; return outMin+(v-min)/(max-min)*(outMax-outMin)}
function niceMax(v){if(!v)return 1; const p=10**Math.floor(Math.log10(v)); const n=v/p; return (n<=1?1:n<=2?2:n<=5?5:10)*p}
function svgBase(container,w=700,h=330){clear(container);const svg=svgEl('svg',{viewBox:`0 0 ${w} ${h}`,preserveAspectRatio:'xMidYMid meet','aria-hidden':'true'});container.appendChild(svg);return svg}
function addTitle(el,text){const t=svgEl('title');t.textContent=text;el.appendChild(t)}
function lineChart(container, labels, series, opts={}){
  const svg=svgBase(container,760,330), m={l:55,r:20,t:22,b:48}, W=760-m.l-m.r,H=330-m.t-m.b;
  const all=series.flatMap(s=>s.values).filter(Number.isFinite), min=opts.zero?0:Math.min(...all), max=niceMax(Math.max(...all));
  for(let i=0;i<=4;i++){const y=m.t+H*i/4;svg.appendChild(svgEl('line',{x1:m.l,x2:m.l+W,y1:y,y2:y,class:'grid-line'}));const txt=svgEl('text',{x:m.l-8,y:y+4,'text-anchor':'end'});txt.textContent=opts.formatY?opts.formatY(max-(max-min)*i/4):fmt.compact(max-(max-min)*i/4);svg.appendChild(txt)}
  const step=labels.length>1?W/(labels.length-1):W;
  const every=Math.max(1,Math.ceil(labels.length/7)); labels.forEach((l,i)=>{if(i%every===0||i===labels.length-1){const t=svgEl('text',{x:m.l+i*step,y:315,'text-anchor':'middle'});t.textContent=l;svg.appendChild(t)}});
  series.forEach((s,si)=>{
    const pts=s.values.map((v,i)=>[m.l+i*step,m.t+H-scaleLinear(v,min,max,0,H)]);
    if(opts.area&&si===0){let d=`M${pts[0][0]},${m.t+H} `+pts.map(p=>`L${p[0]},${p[1]}`).join(' ')+` L${pts.at(-1)[0]},${m.t+H} Z`;svg.appendChild(svgEl('path',{d,class:'area'}))}
    const path=svgEl('path',{d:pts.map((p,i)=>(i?'L':'M')+p.join(',')).join(' '),class:`line ${si?'secondary':''}`,stroke:s.color||undefined});svg.appendChild(path);
    pts.forEach((p,i)=>{if(labels.length<45||i%every===0){const c=svgEl('circle',{cx:p[0],cy:p[1],r:3.5,class:'dot tooltip-target',fill:s.color||undefined});addTitle(c,`${labels[i]} · ${s.name}: ${opts.tooltipFormat?opts.tooltipFormat(s.values[i]):fmt.compact(s.values[i])}`);svg.appendChild(c)}})
  });
  if(series.length>1){series.forEach((s,i)=>{const x=m.l+i*130;const line=svgEl('line',{x1:x,y1:12,x2:x+20,y2:12,stroke:s.color||[colors.gold,colors.emerald][i], 'stroke-width':3});svg.appendChild(line);const t=svgEl('text',{x:x+27,y:16});t.textContent=s.name;svg.appendChild(t)})}
}
function barChart(container, items, opts={}){
  const horizontal=opts.horizontal!==false, maxItems=opts.maxItems||items.length, data=items.slice(0,maxItems);
  const h=Math.max(260,data.length*30+60),svg=svgBase(container,760,h),m={l:horizontal?135:45,r:30,t:20,b:horizontal?25:55},W=760-m.l-m.r,H=h-m.t-m.b,max=niceMax(Math.max(...data.map(d=>d.value),1));
  if(horizontal){const row=H/data.length;data.forEach((d,i)=>{const y=m.t+i*row+row*.18,bh=row*.58,w=W*d.value/max;const label=svgEl('text',{x:m.l-10,y:y+bh*.72,'text-anchor':'end'});label.textContent=d.label.length>18?d.label.slice(0,17)+'…':d.label;svg.appendChild(label);const rect=svgEl('rect',{x:m.l,y,width:Math.max(1,w),height:bh,rx:2,class:'bar tooltip-target',fill:d.color||opts.color||colors.gold});addTitle(rect,`${d.label}: ${opts.format?opts.format(d.value):fmt.compact(d.value)}`);svg.appendChild(rect);const val=svgEl('text',{x:Math.min(m.l+w+7,735),y:y+bh*.72});val.textContent=opts.format?opts.format(d.value):fmt.compact(d.value);svg.appendChild(val)})}
  else{const col=W/data.length;for(let i=0;i<=4;i++){const y=m.t+H*i/4;svg.appendChild(svgEl('line',{x1:m.l,x2:m.l+W,y1:y,y2:y,class:'grid-line'}))}data.forEach((d,i)=>{const w=col*.58,x=m.l+i*col+col*.21,bh=H*d.value/max,y=m.t+H-bh;const r=svgEl('rect',{x,y,width:w,height:bh,rx:2,class:'bar tooltip-target',fill:d.color||opts.color||colors.gold});addTitle(r,`${d.label}: ${opts.format?opts.format(d.value):fmt.compact(d.value)}`);svg.appendChild(r);const t=svgEl('text',{x:x+w/2,y:m.t+H+16,'text-anchor':'middle'});t.textContent=d.label;svg.appendChild(t);const v=svgEl('text',{x:x+w/2,y:y-6,'text-anchor':'middle'});v.textContent=opts.format?opts.format(d.value):fmt.compact(d.value);svg.appendChild(v)})}
}
function donutChart(container, items){const svg=svgBase(container,360,260),cx=180,cy=120,r=78,total=items.reduce((a,b)=>a+b.value,0),circ=2*Math.PI*r;let off=0;items.forEach(d=>{const len=circ*d.value/total;const c=svgEl('circle',{cx,cy,r,fill:'none',stroke:d.color,'stroke-width':28,'stroke-dasharray':`${len} ${circ-len}`,'stroke-dashoffset':-off,transform:`rotate(-90 ${cx} ${cy})`,class:'tooltip-target'});addTitle(c,`${d.label}: ${fmt.pct(d.value)}`);svg.appendChild(c);off+=len});const big=svgEl('text',{x:cx,y:cy-2,'text-anchor':'middle',style:'font-size:28px;fill:#e8c982;font-family:Georgia'});big.textContent='3.00';svg.appendChild(big);const sm=svgEl('text',{x:cx,y:cy+20,'text-anchor':'middle'});sm.textContent='avg days';svg.appendChild(sm)}
function heatmap(container,matrix){const keys=matrix.map(r=>r.metric),cols=Object.keys(matrix[0]).filter(k=>k!=='metric'),cell=34,left=135,top=65,w=left+cols.length*cell+20,h=top+keys.length*cell+30,svg=svgBase(container,w,h);cols.forEach((c,i)=>{const t=svgEl('text',{x:left+i*cell+cell/2,y:top-8,'text-anchor':'end',transform:`rotate(-45 ${left+i*cell+cell/2} ${top-8})`});t.textContent=c.replaceAll('_',' ');svg.appendChild(t)});matrix.forEach((r,ri)=>{const label=svgEl('text',{x:left-8,y:top+ri*cell+22,'text-anchor':'end'});label.textContent=r.metric.replaceAll('_',' ');svg.appendChild(label);cols.forEach((c,ci)=>{const v=Number(r[c]);const alpha=.12+Math.abs(v)*.75;const fill=v>=0?`rgba(109,155,116,${alpha})`:`rgba(198,107,93,${alpha})`;const rect=svgEl('rect',{x:left+ci*cell,y:top+ri*cell,width:cell-2,height:cell-2,fill,class:'tooltip-target'});addTitle(rect,`${r.metric} × ${c}: ${v.toFixed(3)}`);svg.appendChild(rect)})})}
function scatterSynthetic(container){const svg=$('#scatterChart');clear(svg);const pts=[];for(let i=0;i<54;i++){const x=35+i*7.6;const base=250-(i*3.4);const y=Math.max(25,Math.min(260,base+(Math.sin(i*1.7)*28)+(i%4)*6));pts.push([x,y])}for(let i=0;i<=4;i++){svg.appendChild(svgEl('line',{x1:35,x2:470,y1:25+i*58,y2:25+i*58,stroke:'rgba(216,179,106,.12)'}))}pts.forEach(([x,y],i)=>{const c=svgEl('circle',{cx:x,cy:y,r:4,fill:i%6===0?colors.gold:colors.bronze,opacity:.75});svg.appendChild(c)});svg.appendChild(svgEl('path',{d:'M35,245 L470,70',stroke:colors.coral,'stroke-width':2,fill:'none','stroke-dasharray':'7 6'}));const t=svgEl('text',{x:325,y:88,fill:colors.muted});t.textContent='r = −0.483';svg.appendChild(t)}
function saveSVG(id){const svg=$(`#${id} svg`);if(!svg){toast('Chart is not available yet');return}const blob=new Blob([`<?xml version="1.0" encoding="UTF-8"?>`+svg.outerHTML],{type:'image/svg+xml'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${id}.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500);toast('SVG chart saved')}

// Header, navigation, reveal
const header=$('#siteHeader');window.addEventListener('scroll',()=>header.classList.toggle('scrolled',scrollY>20),{passive:true});
$('#menuToggle').addEventListener('click',e=>{const open=$('#navLinks').classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',open);e.currentTarget.setAttribute('aria-label',open?'Close navigation menu':'Open navigation menu');document.body.classList.toggle('menu-open',open)});$$('#navLinks a').forEach(a=>a.addEventListener('click',()=>{$('#navLinks').classList.remove('open');document.body.classList.remove('menu-open');$('#menuToggle').setAttribute('aria-expanded','false');$('#menuToggle').setAttribute('aria-label','Open navigation menu')}));
const observer=new IntersectionObserver(es=>es.forEach(e=>e.isIntersecting&&e.target.classList.add('visible')),{threshold:.08});$$('.reveal').forEach(el=>observer.observe(el));
const sections=$$('main section[id]');const navObs=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){$$('.nav-links a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id))}}),{rootMargin:'-35% 0px -55%'});sections.forEach(s=>navObs.observe(s));
$('#printBtn').addEventListener('click',()=>window.print());$$('.save-chart').forEach(b=>b.addEventListener('click',()=>saveSVG(b.dataset.chart)));

// Metadata and schema
const k=D.kpis;
const metadata=[['Rows',fmt.num(k.records)],['Columns',k.columns],['Date range','2022–2024'],['Brands',k.brands],['SKUs',k.skus],['Categories',k.categories],['Regions',k.regions],['Channels',k.channels],['Missing',k.missing_values]];
$('#metadataStrip').innerHTML=metadata.map(([a,b])=>`<article><span>${a}</span><b>${b}</b></article>`).join('');
const schema=[
['date','Date','Transaction date','2022-01-21'],['sku','Text','Product stock keeping unit','AT-001'],['brand','Text','FMCG brand','Dabur'],['segment','Text','Business segment','Grains-Seg1'],['category','Text','Product category','Atta'],['channel','Text','Sales channel','Online'],['region','Text','Indian sales region','West India'],['pack_type','Text','Packaging format','Packet'],['price_unit','Decimal','Unit selling price','41.10'],['promotion_flag','Integer','Promotion status: 0/1','0'],['delivery_days','Integer','Delivery time from 1 to 5 days','4'],['stock_available','Integer','Available stock proxy','142'],['delivered_qty','Integer','Delivered quantity proxy','191'],['units_sold','Integer','Units sold','78']
];
$('#schemaTable tbody').innerHTML=schema.map(r=>`<tr>${r.map(c=>`<td>${escapeHTML(c)}</td>`).join('')}</tr>`).join('');

// Sample table
let tablePage=1, tableFiltered=[...SAMPLE]; const pageSize=10; const sampleCols=['date','sku','brand','category','channel','region','pack_type','price_unit','promotion_flag','delivery_days','units_sold','revenue'];
const catSelect=$('#tableCategory'), segSelect=$('#tableSegment'), packSelect=$('#tablePack');
[...new Set(SAMPLE.map(r=>r.category))].sort().forEach(v=>catSelect.add(new Option(v,v)));
[...new Set(SAMPLE.map(r=>r.segment))].sort().forEach(v=>segSelect.add(new Option(v,v)));
[...new Set(SAMPLE.map(r=>r.pack_type))].sort().forEach(v=>packSelect.add(new Option(v,v)));
function filterTable(){const q=$('#tableSearch').value.trim().toLowerCase(),cat=catSelect.value,seg=segSelect.value,pack=packSelect.value;tableFiltered=SAMPLE.filter(r=>(!cat||r.category===cat)&&(!seg||r.segment===seg)&&(!pack||r.pack_type===pack)&&(!q||Object.values(r).some(v=>String(v).toLowerCase().includes(q))));tablePage=1;renderTable()}
function renderTable(){const pages=Math.max(1,Math.ceil(tableFiltered.length/pageSize));tablePage=Math.min(tablePage,pages);const rows=tableFiltered.slice((tablePage-1)*pageSize,tablePage*pageSize);$('#sampleTable thead').innerHTML='<tr>'+sampleCols.map(c=>`<th>${c.replaceAll('_',' ')}</th>`).join('')+'</tr>';$('#sampleTable tbody').innerHTML=rows.map(r=>'<tr>'+sampleCols.map(c=>`<td>${c==='revenue'?fmt.compact(Number(r[c])):c==='price_unit'?Number(r[c]).toFixed(2):escapeHTML(r[c])}</td>`).join('')+'</tr>').join('')||'<tr><td colspan="12">No matching sample rows.</td></tr>';$('#tableCount').textContent=`${tableFiltered.length} representative rows`;$('#pageIndicator').textContent=`Page ${tablePage} of ${pages}`;$('#prevPage').disabled=tablePage<=1;$('#nextPage').disabled=tablePage>=pages}
$('#tableSearch').addEventListener('input',filterTable);[catSelect,segSelect,packSelect].forEach(el=>el.addEventListener('change',filterTable));$('#prevPage').addEventListener('click',()=>{tablePage--;renderTable()});$('#nextPage').addEventListener('click',()=>{tablePage++;renderTable()});
$('#exportTable').addEventListener('click',()=>{const csv=[sampleCols.join(','),...tableFiltered.map(r=>sampleCols.map(c=>`"${String(r[c]??'').replaceAll('"','""')}"`).join(','))].join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='filtered_fmcg_sample.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500);toast('Filtered sample exported')});renderTable();

// Filters and cube aggregation
const filterIds={year:'filterYear',brand:'filterBrand',category:'filterCategory',region:'filterRegion',channel:'filterChannel',promotion_flag:'filterPromotion'};
Object.entries(filterIds).forEach(([key,id])=>{if(key==='promotion_flag')return;[...new Set(CUBE.map(r=>String(cubeValue(r,key))))].sort((a,b)=>key==='year'?a-b:a.localeCompare(b)).forEach(v=>$('#'+id).add(new Option(v,v)))});
function state(){return {year:$('#filterYear').value,brand:$('#filterBrand').value,category:$('#filterCategory').value,region:$('#filterRegion').value,channel:$('#filterChannel').value,promotion_flag:$('#filterPromotion').value}}
function filteredCube(){const s=state();return CUBE.filter(r=>Object.entries(s).every(([k,v])=>!v||String(cubeValue(r,k))===String(v)))}
function aggregate(rows){const out=rows.reduce((a,r)=>{a.records+=cubeValue(r,'records');a.revenue+=cubeValue(r,'revenue');a.units+=cubeValue(r,'units');a.stock+=cubeValue(r,'stock');a.delivered+=cubeValue(r,'delivered');a.delivery_sum+=cubeValue(r,'delivery_sum');return a},{records:0,revenue:0,units:0,stock:0,delivered:0,delivery_sum:0});out.fill=out.stock?out.delivered/out.stock*100:0;out.sell=(out.stock+out.delivered)?out.units/(out.stock+out.delivered)*100:0;out.delivery=out.records?out.delivery_sum/out.records:0;return out}
function promoLift(rows){const p=aggregate(rows.filter(r=>Number(cubeValue(r,'promotion_flag'))===1)),n=aggregate(rows.filter(r=>Number(cubeValue(r,'promotion_flag'))===0));return p.records&&n.records?(p.units/p.records)/(n.units/n.records)*100-100:null}
function group(rows,key){const m=new Map;rows.forEach(r=>{const k=cubeValue(r,key);if(!m.has(k))m.set(k,[]);m.get(k).push(r)});return [...m].map(([label,rs])=>({label,...aggregate(rs)})).sort((a,b)=>b.revenue-a.revenue)}
function renderChips(){const s=state(),labels={year:'Year',brand:'Brand',category:'Category',region:'Region',channel:'Channel',promotion_flag:'Promotion'};const chips=Object.entries(s).filter(([,v])=>v).map(([key,v])=>`<span class="chip">${labels[key]}: ${key==='promotion_flag'?(v==='1'?'Yes':'No'):escapeHTML(v)}</span>`);$('#filterChips').innerHTML=chips.join('')||'<span class="chip muted">No filters applied</span>'}
function renderDashboard(){const rows=filteredCube(),a=aggregate(rows),lift=promoLift(rows);const kpis=[
['Total revenue',fmt.cr(a.revenue),'price × units sold','Verified'],['Units sold',fmt.mil(a.units),'sum of units sold','Verified'],['Fill rate',fmt.pct(a.fill),'delivered ÷ stock available',a.fill>=95?'Target met':'Below 95% target'],['Average delivery',`${a.delivery.toFixed(2)} days`,'weighted row average',a.delivery<=2?'Healthy':a.delivery<=4?'Watch':'Critical'],['Sell-through',fmt.pct(a.sell),'units ÷ available supply','Recomputed'],['Promotion lift',lift==null?'Filtered':fmt.pct(lift),'mean unit difference','Observational'],['Records',fmt.num(a.records),'matching analytical records','Cube-backed'],['Revenue / record',a.records?`₹${fmt.num(a.revenue/a.records)}`:'₹0','revenue ÷ records','Context']
];$('#kpiGrid').innerHTML=kpis.map(x=>`<article class="kpi-card"><span class="kpi-status">${x[3]}</span><span class="kpi-label">${x[0]}</span><b>${x[1]}</b><p>${x[2]}</p></article>`).join('');
  const b=group(rows,'brand').map(x=>({label:x.label,value:x.revenue})),c=group(rows,'category').map(x=>({label:x.label,value:x.revenue})),r=group(rows,'region').map(x=>({label:x.label,value:x.revenue})),ch=group(rows,'channel').map(x=>({label:x.label,value:x.revenue}));
  barChart($('#brandChart'),b,{maxItems:10,format:fmt.cr});barChart($('#categoryChart'),c,{maxItems:10,format:fmt.cr});barChart($('#regionChart'),r,{maxItems:5,format:fmt.cr,color:colors.bronze});barChart($('#channelChart'),ch,{maxItems:4,format:fmt.cr,color:colors.emerald});renderMonthly();renderChips();
}
function renderMonthly(){const yr=$('#filterYear').value;let data=D.charts.monthly_trend.filter(x=>!yr||String(x.year)===yr);const maxR=Math.max(...data.map(x=>x.revenue),1),maxU=Math.max(...data.map(x=>x.units_sold),1);lineChart($('#monthlyTrend'),data.map(x=>x.month_period),[{name:'Revenue index',values:data.map(x=>x.revenue/maxR*100),color:colors.gold},{name:'Units index',values:data.map(x=>x.units_sold/maxU*100),color:colors.emerald}],{area:true,zero:true,formatY:v=>`${v.toFixed(0)}%`,tooltipFormat:v=>`${v.toFixed(1)}%`})}
Object.values(filterIds).forEach(id=>$('#'+id).addEventListener('change',renderDashboard));$('#resetFilters').addEventListener('click',()=>{Object.values(filterIds).forEach(id=>$('#'+id).value='');renderDashboard()});
const deliveryItems=D.charts.delivery_status.map((x,i)=>({label:x.delivery_status,value:x.share_pct,color:[colors.emerald,colors.amber,colors.coral][i]}));donutChart($('#deliveryStatus'),deliveryItems);$('#deliveryLegend').innerHTML=deliveryItems.map(x=>`<span><i style="background:${x.color}"></i>${x.label} ${fmt.pct(x.value)}</span>`).join('');renderDashboard();

// Tabs
$$('.analysis-tabs button').forEach(b=>b.addEventListener('click',()=>{$$('.analysis-tabs button').forEach(x=>x.classList.remove('active'));$$('.tab-panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#'+b.dataset.tab).classList.add('active')}));
$$('.view-toggle button').forEach(b=>b.addEventListener('click',()=>{$$('.view-toggle button').forEach(x=>x.classList.remove('active'));$$('.stat-view').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#'+b.dataset.view).classList.add('active')}));
$$('.recommendation-tabs button').forEach(b=>b.addEventListener('click',()=>{$$('.recommendation-tabs button').forEach(x=>x.classList.remove('active'));$$('.recommendation-panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#'+b.dataset.rec).classList.add('active')}));

// Static analysis charts
barChart($('#yearlyRevenue'),D.charts.yearly_trend.map(x=>({label:String(x.year),value:x.revenue})),{horizontal:false,format:fmt.cr});
const cats=D.charts.category_summary.slice().sort((a,b)=>b.revenue-a.revenue),totalCats=cats.reduce((a,b)=>a+b.revenue,0);let cum=0;lineChart($('#paretoChart'),cats.slice(0,12).map(x=>x.category),[{name:'Cumulative %',values:cats.slice(0,12).map(x=>{cum+=x.revenue;return cum/totalCats*100}),color:colors.bronze}],{zero:true,formatY:v=>`${v.toFixed(0)}%`,tooltipFormat:v=>`${v.toFixed(1)}%`});
barChart($('#weekdayChart'),D.charts.weekday_analysis.map(x=>({label:x.day_name,value:x.mean_units,color:x.is_weekend?colors.emerald:colors.gold})),{horizontal:false,format:v=>v.toFixed(1)});
barChart($('#deliveryChannelChart'),D.charts.delivery_by_channel.map(x=>({label:x.channel,value:x.avg_delivery_days,color:x.avg_delivery_days<=2?colors.emerald:x.avg_delivery_days<=4?colors.amber:colors.coral})),{format:v=>`${v.toFixed(2)} d`});
barChart($('#fillRegionChart'),D.charts.supply_chain_by_region.map(x=>({label:x.region,value:x.fill_rate_pct,color:x.fill_rate_pct>=95?colors.emerald:colors.amber})),{format:fmt.pct});
barChart($('#promotionBrandChart'),D.charts.promotion_by_brand.map(x=>({label:x.brand,value:x.unit_lift_pct,color:colors.emerald})),{maxItems:10,format:fmt.pct});
barChart($('#promotionRegionChart'),D.charts.promotion_by_region.map(x=>({label:x.region,value:x.unit_lift_pct,color:colors.bronze})),{maxItems:5,format:fmt.pct});

// Alerts
let alertMode='reorder';
function filteredAlerts(){const s=state();const source=alertMode==='reorder'?D.charts.reorder_alerts:D.charts.overstock_alerts;return source.filter(r=>(!s.brand||r.brand===s.brand)&&(!s.category||r.category===s.category)&&(!s.region||r.region===s.region)&&(!s.channel||r.channel===s.channel))}
function renderAlerts(){const rows=filteredAlerts().slice(0,25),scoreKey=alertMode==='reorder'?'reorder_priority_score':'overstock_risk_score',statusKey=alertMode==='reorder'?'stock_risk_flag':'overstock_flag';$('#alertTable tbody').innerHTML=rows.map(r=>`<tr><td><b>${escapeHTML(r.brand)}</b> · ${escapeHTML(r.sku)}</td><td>${escapeHTML(r.category)}</td><td>${escapeHTML(r.region)}</td><td>${escapeHTML(r.channel)}</td><td>${fmt.num(r.units_sold)}</td><td>${fmt.pct(r.fill_rate_pct)}</td><td>${fmt.pct(r.sell_through_rate_pct)}</td><td>${Number(r[scoreKey]).toFixed(1)}</td><td><span class="status-badge ${String(r[statusKey]).toLowerCase()}">${escapeHTML(r[statusKey])}</span></td></tr>`).join('')||'<tr><td colspan="9">No alert rows match the current filters.</td></tr>'}
$$('.alert-switch button').forEach(b=>b.addEventListener('click',()=>{$$('.alert-switch button').forEach(x=>x.classList.remove('active'));b.classList.add('active');alertMode=b.dataset.alert;renderAlerts()}));Object.values(filterIds).forEach(id=>$('#'+id).addEventListener('change',renderAlerts));renderAlerts();

// Region abstraction
function renderRegion(name='West India'){const r=D.charts.region_summary.find(x=>x.region===name)||D.charts.region_summary[0];$$('#regionMap button').forEach(b=>b.classList.toggle('active',b.dataset.region===r.region));$('#regionDetail').innerHTML=`<p class="eyebrow">Regional profile</p><h3>${r.region}</h3><p>Performance is unusually balanced across regions, which suggests synthetic construction rather than a naturally uneven market.</p><div class="region-kpis"><div><span>Revenue</span><b>${fmt.cr(r.revenue)}</b></div><div><span>Revenue share</span><b>${fmt.pct(r.revenue_share_pct)}</b></div><div><span>Units sold</span><b>${fmt.mil(r.units_sold)}</b></div><div><span>Fill rate</span><b>${fmt.pct(r.fill_rate_pct)}</b></div><div><span>Delivery</span><b>${r.avg_delivery_days.toFixed(2)} days</b></div><div><span>Sell-through</span><b>${fmt.pct(r.sell_through_rate_pct)}</b></div></div>`}
$$('#regionMap button').forEach(b=>b.addEventListener('click',()=>renderRegion(b.dataset.region)));renderRegion();

// Stats
heatmap($('#correlationChart'),D.charts.correlation_matrix);scatterSynthetic();

// Insights
const insights=[
['Tea is the revenue anchor','₹229.70 M','Tea contributes 18.14% of revenue, twice the share of Coffee.','Protect availability while reducing single-category dependence.','Business & Inventory'],
['Milk moves fastest','83.55% STR','Milk has the highest category sell-through and 16.21% of all units sold.','Use tighter replenishment and expiry-aware safety stock.','Inventory'],
['Brand concentration is low','10.24% top share','Dabur leads revenue, but all ten brands sit near 10%, an unusually balanced pattern.','Treat brand ranking differences as modest and avoid exaggerated winner narratives.','Business'],
['Promotions correlate with volume','+28.69% units','Promoted transactions average 19.42 more units; Cohen’s d is 0.353.','Run controlled holdouts before claiming incremental causal impact.','Marketing'],
['Fill rate misses the stated target','90.82%','The verified rate is below the 95% target referenced by the source report.','Audit supplier, warehouse, and replenishment constraints.','Supply Chain'],
['Critical delivery tail matters','19.88%','Nearly one in five records takes more than four days, despite a three-day average.','Manage tail risk by SKU and region, not only average delivery.','Supply Chain'],
['Weekend volume is higher','73.44 Sunday','Saturday and Sunday show the highest average units per record.','Align staffing and inventory for weekend demand, then validate in real data.','Operations'],
['The dataset looks synthetic','Balanced structure','Every brand appears across the SKU space and regional shares are almost equal.','Use this as a portfolio demonstration, not as evidence about a real FMCG company.','All stakeholders']
];
$('#insightStack').innerHTML=insights.map((x,i)=>`<article class="insight-item reveal"><span class="num">${String(i+1).padStart(2,'0')}</span><div><p class="eyebrow">${x[1]}</p><h3>${x[0]}</h3><p>${x[2]}</p><span class="stakeholder-tag">${x[4]}</span></div><div class="insight-action"><span>Recommended action</span><b>${x[3]}</b></div></article>`).join('');$$('#insightStack .reveal').forEach(el=>observer.observe(el));

// Reconciliation table
$('#reconciliationTable tbody').innerHTML=D.reconciliation.slice(0,12).map(r=>`<tr><td>${escapeHTML(r.kpi)}</td><td>${escapeHTML(r.stage5_reported||'—')}</td><td>${escapeHTML(r.presentation_reported||'—')}</td><td>${escapeHTML(r.csv_recomputed||'—')}</td><td>${escapeHTML(r.final_website_value||'—')}</td></tr>`).join('');

// Resource library
const resources=['fmcg_analysis_report.md','fmcg_frontend_data.json','fmcg_kpi_reconciliation.csv','analyze_fmcg.py','fmcg_analysis_tables/brand_summary.csv','fmcg_analysis_tables/category_summary.csv','fmcg_analysis_tables/channel_summary.csv','fmcg_analysis_tables/cleaning_log.csv','fmcg_analysis_tables/correlation_matrix.csv','fmcg_analysis_tables/daily_trend.csv','fmcg_analysis_tables/delivery_by_channel.csv','fmcg_analysis_tables/delivery_distribution.csv','fmcg_analysis_tables/delivery_status_overall.csv','fmcg_analysis_tables/inventory_overstock_alerts_top50.csv','fmcg_analysis_tables/inventory_reorder_alerts_top50.csv','fmcg_analysis_tables/monthly_trend.csv','fmcg_analysis_tables/outlier_summary.csv','fmcg_analysis_tables/pack_type_summary.csv','fmcg_analysis_tables/promotion_by_brand.csv','fmcg_analysis_tables/promotion_by_category.csv','fmcg_analysis_tables/promotion_by_channel.csv','fmcg_analysis_tables/promotion_by_pack_type.csv','fmcg_analysis_tables/promotion_by_price_band.csv','fmcg_analysis_tables/promotion_by_region.csv','fmcg_analysis_tables/promotion_overall.csv','fmcg_analysis_tables/quarterly_trend.csv','fmcg_analysis_tables/region_summary.csv','fmcg_analysis_tables/sample_data_100.csv','fmcg_analysis_tables/segment_summary.csv','fmcg_analysis_tables/sku_summary.csv','fmcg_analysis_tables/supply_chain_by_region.csv','fmcg_analysis_tables/weekday_analysis.csv','fmcg_analysis_tables/yearly_trend.csv'];
$('#resourceGrid').innerHTML=resources.map(r=>`<a href="assets/data/${r}" download title="Download ${r}">${r.split('/').pop()}</a>`).join('');

// Re-apply deep links after dynamic sections have received their final height.
if(location.hash){const target=$(location.hash);if(target)requestAnimationFrame(()=>requestAnimationFrame(()=>target.scrollIntoView({behavior:'instant',block:'start'})))}
})();
