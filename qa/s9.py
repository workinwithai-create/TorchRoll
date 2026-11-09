# TorchRoll AUDIO-ENGINE-RULES section 9 acceptance run (+ MIDI keyboard checks). Usage: python3 qa/s9.py <url> [out.json]
import asyncio, base64, json, sys, io, wave, os, re, subprocess, numpy as np, mido
from playwright.async_api import async_playwright
URL=sys.argv[1]; OUT=sys.argv[2] if len(sys.argv)>2 else 'checks/s9.json'; OD=os.path.join(os.path.dirname(os.path.abspath(OUT)),'out'); os.makedirs(OD,exist_ok=True)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); F="window.__torchroll"; HIDE_S=int(os.environ.get('HIDE_S','30'))
MOCK="""(()=>{ const sent=[]; window.__midiSent=sent; const inp={id:'in1',name:'Mock Keys 49',type:'input',state:'connected',onmidimessage:null}; const out={id:'out1',name:'Mock Synth Out',type:'output',state:'connected',send:(d,t)=>sent.push({d:[...d],t})};
 const acc={inputs:new Map([['in1',inp]]),outputs:new Map([['out1',out]]),onstatechange:null}; window.__mockIn=inp; navigator.requestMIDIAccess=()=>Promise.resolve(acc); })();"""
B64="""async o=>{ const r=await window.__torchroll.exportWavBytes(o||{}); const b=r.bytes; let s=''; for(let i=0;i<b.length;i+=32768) s+=String.fromCharCode.apply(null,b.subarray(i,i+32768)); return {name:r.name,b64:btoa(s),frames:r.frames}; }"""
MID="""()=>{ const r=window.__torchroll.exportMidBytes(); const b=r.bytes; let s=''; for(let i=0;i<b.length;i++) s+=String.fromCharCode(b[i]); return {name:r.name,b64:btoa(s)}; }"""
def load(b):
  w=wave.open(io.BytesIO(b)); n=w.getnframes(); raw=np.frombuffer(w.readframes(n),dtype=np.uint8).reshape(-1,3)
  v=(raw[:,0].astype(np.int32)|(raw[:,1].astype(np.int32)<<8)|(raw[:,2].astype(np.int32)<<16)); v[v>=1<<23]-=1<<24
  return w.getframerate(),w.getsampwidth(),n,(v/8388607.0).reshape(-1,w.getnchannels()),w.getnchannels()
async def wav(pg,o=None):
  r=await pg.evaluate(B64,o or {}); return r['name'],base64.b64decode(r['b64'])
async def midi(pg,data): await pg.evaluate("d=>window.__mockIn.onmidimessage({data:new Uint8Array(d)})",data)
PEAK="""async()=>{const an=window.__torchroll.bus().an, x=new Float32Array(an.fftSize); let p=0; for(let i=0;i<12;i++){ an.getFloatTimeDomainData(x); for(const v of x) p=Math.max(p,Math.abs(v)); await new Promise(r=>setTimeout(r,25)); } return p}"""
rms=lambda a: float(np.sqrt((np.asarray(a,dtype=np.float64)**2).mean())) if len(a) else 0.0
async def main():
  res={}
  async with async_playwright() as p:
    br=await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx=await br.new_context(viewport={'width':1360,'height':1100},accept_downloads=True); await ctx.add_init_script(MOCK); pg=await ctx.new_page(); errs=[]; reqs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text)); pg.on('request',lambda r: reqs.append(r.url))
    await pg.goto(URL); await pg.evaluate("()=>localStorage.clear()"); await pg.reload(); await pg.screenshot(path=OD+'/shot-tap.png')
    await pg.click('#tapBtn'); await pg.wait_for_function(f"{F}.ctx() && {F}.ctx().state==='running'"); await pg.wait_for_timeout(300)
    res['live_ctx']=await pg.evaluate(f"()=>({{sampleRate:{F}.ctx().sampleRate,state:{F}.ctx().state,status:document.getElementById('status').textContent,midiNote:document.getElementById('midiNote').textContent}})")
    await pg.wait_for_function(f"{F}.ctx().currentTime>0.3")
    await midi(pg,[0x90,57,110]); await pg.wait_for_timeout(100)
    a=await pg.evaluate(f"()=>({{voices:{F}.liveVoices(),playing:!!{F}.play()}})"); a['peak']=await pg.evaluate(PEAK)
    await midi(pg,[0xB0,64,127]); await midi(pg,[0x80,57,0]); await pg.wait_for_timeout(200); sus=await pg.evaluate(f"()=>({{voices:{F}.liveVoices(),sustain:{F}.sustainOn()}})")
    await midi(pg,[0xB0,64,0]); await pg.wait_for_timeout(200); rel=await pg.evaluate(f"()=>{F}.liveVoices()")
    await pg.wait_for_timeout(600); await midi(pg,[0x90,57,20]); await pg.wait_for_timeout(100); soft=await pg.evaluate(PEAK); await midi(pg,[0x80,57,0])
    await midi(pg,[0xB0,1,64]); depth=await pg.evaluate(f"()=>{F}.state.trem"); await midi(pg,[0xB0,1,127])
    await midi(pg,[0xF8]); await midi(pg,[0xFA]); trans=await pg.evaluate(f"()=>!!{F}.play()")
    await pg.select_option('#midiOut','out1'); await midi(pg,[0x90,64,90]); await midi(pg,[0x80,64,0]); sent=await pg.evaluate("()=>window.__midiSent.map(m=>m.d)")
    sel=await pg.evaluate("()=>({in:[...document.getElementById('midiIn').options].map(o=>o.text),out:[...document.getElementById('midiOut').options].map(o=>o.text),audioOut:[...document.getElementById('audioOut').options].map(o=>o.text)})")
    res['midi']={'note_on_voices':a['voices'],'note_on_transport_started':a['playing'],'note_on_output_peak':round(a['peak'],4),'velocity20_peak':round(soft,4),'sustain_held_after_noteoff':sus,'voices_after_cc64_up':rel,'cc1_64_tremDepth':depth,'clock_start_msgs_start_transport':trans,
      'midi_out_sent':sent[:4],'selects':sel}
    res['midi']['pass']=a['voices']==1 and not a['playing'] and a['peak']>0.01 and soft<a['peak'] and sus['voices']==1 and sus['sustain'] and rel==0 and abs(depth-0.5)<0.02 and not trans and [0x90,64,90] in sent and [0x80,64,0] in sent and 'Mock Keys 49' in sel['in'] and 'Mock Synth Out' in sel['out']
    await pg.screenshot(path=OD+'/shot-ui.png',full_page=True)
    # ---- check 1: 92 BPM, 8 bars, 48 kHz -> exactly 1,001,739 samples
    await pg.evaluate(f"()=>{{const s={F}.setSetting; s('bpm',92); s('bars',8); s('recipe','torch'); s('keyRoot',9); s('mode','minor');}}")
    name,b=await wav(pg); open(OD+'/'+name,'wb').write(b); sr,sw,n,x,nc=load(b); mx=np.abs(x).max(1); fi=int(np.argmax(mx>0.05*mx.max()))
    res['c1_export']={'file':name,'frames':n,'expected':round(8*4*60/92*48000),'sr':sr,'bits':sw*8,'channels':nc,'peak_dBFS':round(20*np.log10(np.abs(x).max()),3),'first_transient_sample':fi,'first_transient_ms':round(fi/48,3)}
    res['c1_export']['pass']=n==1001739 and sr==48000 and sw==3 and nc==2 and res['c1_export']['peak_dBFS']<=-1 and fi<=48 and name=='torchroll-torch-92bpm-Am.wav'
    # ---- check 2: loop 4x
    L=np.tile(x,(4,1)); d=np.abs(np.diff(L[:,0])); seams=[n*k for k in (1,2,3)]; seam_jump=max(float(d[s-1]) for s in seams); typ=float(np.percentile(d,99.9)); med=float(np.median(d))
    _,bk=await wav(pg,{'only':['drums']}); xk=load(bk)[3][:,0]; LK=np.tile(xk,4); bar=n/8; on=[]
    for k in range(32):
      e=int(round(k*bar)); w=np.abs(LK[e:e+480]); on.append(int(np.argmax(w>0.05*w.max())) if w.max()>0 else 0)
    res['c2_loop']={'seam_jump':round(seam_jump,5),'p99_9_step':round(typ,5),'median_step':round(med,6),'kick_onset_vs_bar_line_samples_4x':sorted(set(on)),'bar_len_samples':bar}
    res['c2_loop']['pass']=seam_jump<=typ and max(on)-min(on)<=4 and max(on)<=48
    # ---- MIDI file
    mm=await pg.evaluate(MID); fn=OD+'/'+mm['name']; open(fn,'wb').write(base64.b64decode(mm['b64'])); mf=mido.MidiFile(fn)
    names=[next((e.name for e in t if e.type=='track_name'),'') for t in mf.tracks]; tempos=[e.tempo for e in mf.tracks[0] if e.type=='set_tempo']; ts=[(e.numerator,e.denominator) for e in mf.tracks[0] if e.type=='time_signature']
    lens=[sum(e.time for e in t) for t in mf.tracks]
    res['midi_file']={'file':mm['name'],'type':mf.type,'tracks':names,'tempo_bpm':[round(mido.tempo2bpm(t),3) for t in tempos],'timesig':ts,'track_len_ticks':sorted(set(lens)),'expected_ticks':8*4*480}
    res['midi_file']['pass']=mm['name']=='torchroll-torch-92bpm-Am.mid' and len(tempos)==1 and abs(mido.tempo2bpm(tempos[0])-92)<0.01 and ts==[(4,4)] and set(lens)=={8*4*480} and all(any(w in s for s in names) for w in ('Torch Keys','Breath Pad','Velvet Bass','Brush Kit'))
    # ---- check 4: live changes
    await pg.evaluate(f"()=>{F}.start()"); await pg.wait_for_timeout(1500); p0=await pg.evaluate(f"()=>({{n:window.__schedLog.length,t:{F}.ctx().currentTime}})")
    await pg.evaluate(f"()=>{F}.setSetting('recipe','triplets')"); t_rec=await pg.evaluate(f"()=>{F}.ctx().currentTime"); await pg.wait_for_timeout(1200)
    await pg.evaluate(f"()=>{F}.setSetting('mute',['drums',true])"); t_mut=await pg.evaluate(f"()=>{F}.ctx().currentTime"); await pg.wait_for_timeout(1200)
    await pg.evaluate(f"()=>{F}.setSetting('bpm',128)"); t_bpm=await pg.evaluate(f"()=>{F}.ctx().currentTime"); await pg.wait_for_timeout(1500)
    log=await pg.evaluate("()=>window.__schedLog"); stopped=await pg.evaluate(f"()=>{{{F}.stop(); return {F}.play()}}")
    def first(cond,after):
      for e in log:
        if e['t']>after and cond(e): return e
    bar92=4*60/92
    e1=first(lambda e:e['recipe']=='triplets',t_rec); e2=first(lambda e:e['mutes']['drums'],t_mut); e3=first(lambda e:abs(e['sd']-60/128/3)<1e-9,t_bpm)
    ks=[e['k'] for e in log]; cont=all((ks[i+1]-ks[i])%96==1 for i in range(len(ks)-1)); ts_=[e['t'] for e in log]; mono=all(ts_[i+1]>ts_[i] for i in range(len(ts_)-1))
    pick_ok=all(((e['pattern'][e['k']%12]!='-')==bool(e.get('keysOn'))) or e['recipe']=='hold' for e in log)
    res['c4_live']={'recipe_heard_after_s':round(e1['t']-t_rec,3) if e1 else None,'mute_heard_after_s':round(e2['t']-t_mut,3) if e2 else None,'bpm_heard_after_s':round(e3['t']-t_bpm,3) if e3 else None,'one_bar_s_at_92':round(bar92,3),
      'steps_continuous_no_restart':cont,'audio_clock_times_increasing':mono,'keys_follow_current_pattern_every_step':pick_ok,'steps_logged':len(log),'stop_clears_transport':stopped is None}
    res['c4_live']['pass']=bool(e1 and e2 and e3 and e1['t']-t_rec<bar92 and e2['t']-t_mut<bar92 and e3['t']-t_bpm<bar92 and cont and mono and pick_ok and stopped is None)
    # Stop silences
    await pg.evaluate(f"()=>{{{F}.setSetting('mute',['drums',false]); {F}.start(); {F}.liveOn(60,1,'qa'); {F}.liveOn(64,1,'qa');}}"); await pg.wait_for_timeout(1200)
    sil=await pg.evaluate(f"""async()=>{{const an={F}.bus().an, a=new Float32Array(an.fftSize), t0=performance.now(); {F}.stop(); for(let i=0;i<300;i++){{ await new Promise(r=>setTimeout(r,2)); an.getFloatTimeDomainData(a); let p=0; for(const x of a) p=Math.max(p,Math.abs(x)); if(p<0.001) return {{ms:performance.now()-t0,peak:p,live:{F}.liveVoices()}}; }} return {{ms:null}}; }}""")
    res['stop_silence']=dict(sil,pass_=sil.get('ms') is not None and sil['ms']<120)
    # ---- check 3: hide tab
    await pg.evaluate(f"()=>{F}.start()"); await pg.wait_for_timeout(1500); oth=await ctx.new_page(); await oth.goto('about:blank'); await oth.bring_to_front()
    n0=await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{value:'hidden',configurable:true});document.dispatchEvent(new Event('visibilitychange'));return window.__schedLog.length}")
    await pg.wait_for_timeout(HIDE_S*1000); await pg.bring_to_front(); await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{value:'visible',configurable:true});document.dispatchEvent(new Event('visibilitychange'))}"); await pg.wait_for_timeout(1500); await oth.close()
    c3=await pg.evaluate(f"()=>{{const an={F}.bus().an, a=new Float32Array(an.fftSize); an.getFloatTimeDomainData(a); let p=0; for(const x of a) p=Math.max(p,Math.abs(x)); return {{playing:!!{F}.play(),log:window.__schedLog.length,sources:{F}.activeSources(),peak:p,status:document.getElementById('status').textContent,btn:document.getElementById('play').textContent}}}}")
    res['c3_hidden']={'hidden_for_s':HIDE_S,'steps_scheduled_after_hide':c3['log']-n0,'playing_after_return':c3['playing'],'output_peak_after_return':round(c3['peak'],6),'status':c3['status'],'play_button':c3['btn']}
    res['c3_hidden']['pass']=not c3['playing'] and c3['log']-n0<=0 and c3['peak']<0.001 and 'Play' in c3['btn']
    # ---- check 6: hold sustain
    await pg.evaluate(f"()=>{{const s={F}.setSetting; s('recipe','hold'); s('bpm',60); s('bars',8); {F}.state.trem=0; {F}.state.take=[57,60,64].map(n=>({{s:0,d:96,n,v:0.8}}));}}")
    _,b6=await wav(pg,{'only':['keys'],'noFold':True}); x6=load(b6)[3][:,0]; N6=len(x6); w=48000//2
    seg=[rms(x6[i:i+w]) for i in range(0,N6-w+1,w)]; early=seg[2]; late=seg[-1]
    res['c6_sustain']={'bpm':60,'note_len_s':32.0,'frames':N6,'rms_at_1s':round(early,5),'rms_last_0.5s':round(late,5),'ratio_last_vs_1s':round(late/early,3) if early else 0,'min_rms_any_half_second':round(min(seg[1:]),5) if seg[1:] else 0}
    res['c6_sustain']['pass']=N6==round(32*48000) and early>0 and late/early>0.7 and min(seg[1:])>0.5*early
    await pg.evaluate(f"()=>{{ {F}.state.take=[]; {F}.setSetting('chordsText','Am9'); }}"); _,bp=await wav(pg,{'only':['pad'],'noFold':True}); xp=load(bp)[3][:,0]
    segp=[rms(xp[i:i+w]) for i in range(0,len(xp)-w+1,w)]; res['c6_sustain']['pad']={'chord':'Am9 tied 8 bars = 32 s','rms_at_1s':round(segp[2],5),'rms_last_0.5s':round(segp[-1],5),'min_rms_after_attack':round(min(segp[2:]),5)}
    res['c6_sustain']['pass']=res['c6_sustain']['pass'] and segp[-1]>0.85*segp[2] and min(segp[2:])>0.8*segp[2]
    await midi(pg,[0xB0,1,0]); await midi(pg,[0x90,57,100]); await midi(pg,[0x90,64,100]); pk=[]
    for i in range(8):
      await pg.wait_for_timeout(500); pk.append(await pg.evaluate(f"()=>{{const an={F}.bus().an, x=new Float32Array(an.fftSize); an.getFloatTimeDomainData(x); let p=0; for(const v of x) p=Math.max(p,Math.abs(v)); return p}}"))
    await midi(pg,[0x80,57,0]); await midi(pg,[0x80,64,0]); res['c6_sustain']['live_hold_peaks_every_0.5s']=[round(v,4) for v in pk]; res['c6_sustain']['pass']=res['c6_sustain']['pass'] and min(pk)>0.3*max(pk) if pk and max(pk)>0 else False
    # ---- check 5: N/A synth-only
    ext=sorted(set(u.split('/')[2] for u in reqs if u.startswith('http') and URL.split('/')[2] not in u))
    pg2=await ctx.new_page(); blocked=[]
    async def block(route):
      blocked.append(route.request.url); await route.abort()
    await pg2.route(re.compile(r'^(?!'+re.escape(URL.rstrip('/'))+').*'),block)
    await pg2.goto(URL); await pg2.click('#tapBtn'); await pg2.wait_for_function(f"{F}.ctx() && {F}.ctx().state==='running'"); ok=await pg2.evaluate(f"()=>{{const r={F}.start(); {F}.stop(); return r}}")
    res['c5_blocked_host']={'result':'N/A: no sample host. Every voice is synthesized in the browser and named as a synth, so there is nothing to block.','third_party_hosts_requested':ext,'requests_blocked_when_all_other_hosts_blocked':blocked,'plays_with_all_other_hosts_blocked':ok}
    res['c5_blocked_host']['pass']=ext==[] and ok
    await pg2.close()
    # ---- check 7
    g=subprocess.run(['bash',ROOT+'/qa/no_unpinned.sh',URL],capture_output=True,text=True); open(os.path.dirname(os.path.abspath(OUT))+'/grep-c7.txt','w').write(g.stdout+g.stderr)
    vn=await pg.evaluate(f"()=>[...Object.values({F}.VOICES).map(v=>v.name),...{F}.CHAIRS.map(c=>c.name)]")
    res['c7_grep']={'script':'qa/no_unpinned.sh','exit':g.returncode,'tail':g.stdout.strip().splitlines()[-1:],'voice_names':vn}
    res['c7_grep']['pass']=g.returncode==0 and all('synth' in v.lower() for v in vn)
    # ---- persistence + license gate
    await pg.reload(); pers=await pg.evaluate(f"()=>({{bpm:{F}.state.bpm,recipe:{F}.state.recipe,bars:{F}.state.bars,key:{F}.state.keyRoot}})")
    gate=await pg.evaluate(f"()=>({{gated:{F}.gated(),buy:document.getElementById('buy').textContent,lic:document.getElementById('licState').textContent}})")
    res['persist_and_gate']={'after_reload':pers,'gate':gate,'pass':pers['bpm']==60 and pers['recipe']=='hold' and not gate['gated'] and 'Checkout opening soon' in gate['buy']}
    res['page_errors']=errs
    res['summary']={k:v.get('pass',v.get('pass_')) for k,v in res.items() if isinstance(v,dict) and ('pass' in v or 'pass_' in v)}
    await br.close()
  json.dump(res,open(OUT,'w'),indent=1); print(json.dumps(res['summary'],indent=1)); print('errors',errs)
asyncio.run(main())
