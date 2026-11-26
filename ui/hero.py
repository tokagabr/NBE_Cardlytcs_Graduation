"""
Landing hero for the Load screen.

Frontend only. It draws no data and calls no pipeline code: an animated scene
that explains the project in one glance (raw transactions are scanned, then
gather into four merchant groups, each with its offer play). It renders inside
an iframe through streamlit.components, so its CSS cannot leak into the app
and the app's CSS cannot break it.
"""

from __future__ import annotations

_HTML = """
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@500;600;800&display=swap" rel="stylesheet">
<style>
  :root{--ink:#0B2A3B;--mut:#5B6E68;--n:#00704A;--n2:#12A06A;--o:#F9A61A;--bl:#3A63B8;--p:#fff;--ln:rgba(11,42,59,.1)}
  *{box-sizing:border-box}
  html,body{margin:0;background:transparent;font-family:'Urbanist','Inter',Arial,sans-serif;color:var(--ink)}
  .h{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:28px;align-items:center;height:100%;padding:8px 4px}
  .h>div:first-child{padding-bottom:110px}
  .eb{display:inline-block;background:rgba(0,112,74,.1);color:var(--n);font-weight:800;font-size:12px;letter-spacing:.09em;border-radius:999px;padding:8px 15px}
  h1{margin:18px 0 14px;font-size:clamp(34px,5vw,60px);line-height:1;font-weight:800;letter-spacing:-.035em}
  h1 span{display:block;animation:rv 1s cubic-bezier(.2,.7,.2,1) backwards}
  h1 span:nth-child(2){animation-delay:.35s;color:var(--n2)}
  p{margin:0;font-size:clamp(15px,1.5vw,19px);line-height:1.55;color:var(--mut);max-width:480px}
  .hint{margin-top:22px;display:inline-flex;align-items:center;gap:10px;font-weight:800;color:var(--n);animation:fy 2s infinite}
  @keyframes rv{from{clip-path:inset(-20% 100% -20% 0);transform:translateY(14px)}to{clip-path:inset(-20% -5% -20% -5%)}}
  @keyframes fy{50%{transform:translateY(6px)}}
  .stg{position:relative;width:100%;aspect-ratio:5/4;max-height:500px}
  .stg:before{content:"";position:absolute;inset:-6%;background:radial-gradient(40% 40% at 25% 30%,rgba(18,160,106,.25),transparent 70%),radial-gradient(35% 35% at 75% 70%,rgba(249,166,26,.25),transparent 70%);filter:blur(10px);animation:bl 10s ease-in-out infinite alternate}
  @keyframes bl{to{transform:translate(3%,-3%) scale(1.08)}}
  canvas{position:absolute;inset:0;width:100%;height:100%}
  .l{position:absolute;transform:translate(-50%,-50%) scale(.85);opacity:0;transition:opacity .6s,transform .4s;background:var(--p);border:1px solid var(--ln);border-left:5px solid var(--c);border-radius:14px;padding:7px 12px;box-shadow:0 10px 26px rgba(11,42,59,.1);white-space:nowrap}
  .l.on{opacity:1;transform:translate(-50%,-50%) scale(1)}.l:hover{transform:translate(-50%,-58%) scale(1.06)}
  .l small{display:block;font-size:10px;color:var(--mut);font-weight:600}.l b{font-size:14px}
  .bc{position:absolute;left:-2%;top:42%;width:112px;aspect-ratio:1.586;border-radius:12px;background:linear-gradient(135deg,#00A060,#005C38);color:#fff;padding:10px;box-shadow:0 18px 36px -14px rgba(0,60,40,.6);transform:rotate(-9deg);animation:cf 5s ease-in-out infinite;font-weight:800;z-index:1;font-size:10px;letter-spacing:.14em}
  @keyframes cf{50%{transform:rotate(-4deg) translateY(-10px)}}
  .bc i{display:block;width:22px;height:16px;border-radius:4px;background:linear-gradient(135deg,#FFD58A,#F9A61A);margin:12px 0 7px}
  @media(max-width:700px){.h{grid-template-columns:1fr;gap:14px}.h>div:first-child{padding-bottom:0}.stg{max-height:230px}h1{font-size:30px;margin:14px 0 10px}p{font-size:15px}}
  @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
<div class="h">
  <div>
    <span class="eb">&#10022; MERCHANT INTELLIGENCE</span>
    <h1><span>Group merchants.</span><span>Match offers.</span></h1>
    <p>Upload card transactions. Get the right offer for every kind of merchant.</p>
  </div>
  <div class="stg" id="stg"><canvas id="cv"></canvas>
    <div class="bc">NBE<i></i>&bull;&bull;&bull;&bull; 4821</div>
  </div>
</div>
<script>
const CL=[[.24,.3,'Frequent Low-Ticket','Cashback on repeat visits',60,.13,'#12A06A'],[.74,.26,'High-Ticket Opportunity','Instalment plans',40,.1,'#F9A61A'],[.26,.72,'VIP-Driven High-Value','Premium partner rewards',32,.88,'#0B2A3B'],[.72,.7,'Mass-Driven High-Reach','Seasonal campaigns',22,.9,'#3A63B8']];
const rm=matchMedia('(prefers-reduced-motion:reduce)').matches,st=document.getElementById('stg'),cv=document.getElementById('cv'),x=cv.getContext('2d'),D=Math.min(devicePixelRatio||1,2);
const lb=CL.map(c=>{const d=document.createElement('div');d.className='l';d.style.cssText='left:'+c[0]*100+'%;top:'+c[5]*100+'%;--c:'+c[6];d.innerHTML='<small>'+c[2]+'</small><b>'+c[3]+'</b>';st.appendChild(d);return d});
let q=7;const r=()=>(q=(q*1664525+1013904223)>>>0)/4294967296,P=[];
CL.forEach((c,g)=>{for(let k=0;k<c[4];k++){const a=r()*6.28,d=Math.sqrt(r())*.1;P.push({g,hx:c[0]+Math.cos(a)*d*.8,hy:c[1]+Math.sin(a)*d,sx:r(),sy:r(),x:r(),y:r(),k:0,r:2.5+r()*3.5,ph:r()*6.28})}});
let mx=-9,my=-9;cv.onpointermove=e=>{const b=cv.getBoundingClientRect();mx=(e.clientX-b.left)/b.width;my=(e.clientY-b.top)/b.height};cv.onpointerleave=()=>mx=my=-9;
const t0=performance.now(),lr=rm?1:.06;
function f(now){const W=cv.clientWidth,H=cv.clientHeight;if(cv.width!==Math.round(W*D)){cv.width=Math.round(W*D);cv.height=Math.round(H*D)}x.setTransform(D,0,0,D,0,0);x.clearRect(0,0,W,H);
const T=((now-t0)/1000)%12,sc=rm?1.2:T<1?-.1:T<7?-.1+(T-1)/6*1.2:T<10?1.2:-.1;
CL.forEach((c,i)=>{const a=Math.max(0,Math.min(1,(sc-c[0])*3))*.16,g=x.createRadialGradient(c[0]*W,c[1]*H,0,c[0]*W,c[1]*H,W*.2);g.addColorStop(0,c[6]);g.addColorStop(1,'rgba(255,255,255,0)');x.globalAlpha=a;x.fillStyle=g;x.fillRect(0,0,W,H);lb[i].classList.toggle('on',sc>c[0])});
for(const p of P){const gr=sc>p.sx,tx=gr?p.hx+Math.cos(now/900+p.ph)*.008:p.sx+Math.cos(now/1500+p.ph)*.012,ty=gr?p.hy+Math.sin(now/1100+p.ph)*.01:p.sy+Math.sin(now/1700+p.ph)*.012;p.x+=(tx-p.x)*lr;p.y+=(ty-p.y)*lr;p.k+=((gr?1:0)-p.k)*lr*1.4;
const dx=p.x-mx,dy=(p.y-my)*H/W,d=Math.hypot(dx,dy);if(d<.1&&d>0){p.x+=dx/d*(.1-d)*.2;p.y+=dy/d*(.1-d)*.2*W/H}
const px=p.x*W,py=p.y*H;x.globalAlpha=(1-p.k)*.6;x.fillStyle='#8DA39A';x.beginPath();x.arc(px,py,p.r*.75,0,6.28);x.fill();x.globalAlpha=p.k*.9;x.fillStyle=CL[p.g][6];x.beginPath();x.arc(px,py,p.r,0,6.28);x.fill()}
if(sc>-.05&&sc<1.1){const sx=sc*W,g=x.createLinearGradient(sx-40,0,sx,0);g.addColorStop(0,'rgba(249,166,26,0)');g.addColorStop(1,'#F9A61A');x.globalAlpha=.35;x.fillStyle=g;x.fillRect(sx-40,0,40,H);x.globalAlpha=1;x.fillStyle='#F9A61A';x.fillRect(sx-1,0,2,H)}
x.globalAlpha=1;if(!rm)requestAnimationFrame(f)}
requestAnimationFrame(f);
</script>
"""


def landing_hero(height: int = 520) -> None:
    """Render the animated landing hero. Safe to call on any screen."""
    import streamlit.components.v1 as components

    components.html(_HTML, height=height, scrolling=False)
