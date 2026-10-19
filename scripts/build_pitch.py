"""Build an offline HTML speaking deck. Font and base CSS are explicit local inputs."""
import argparse
import base64
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLIDES = [
    ("Face liveness before capture acceptance",
     '<p class="lead">Offline verification for resident capture, operator checks, and supervisor checks.</p>'
     '<div class="face-diagram"><div class="face-outline"></div><div class="scan-line"></div><span>Quality + PAD + policy</span></div>'
     '<p class="strap">MOSIP Decode 2026 / Problem 04</p>',
     'State the team name. Explain that the project is a research prototype. Do not claim completed native integration.'),
    ("A returned image is only the beginning",
     '<div class="columns"><div><h2>Presentation</h2><p>Does the incoming stream pass passive PAD and quality checks?</p></div>'
     '<div><h2>Response</h2><p>When required, does the person follow a new, randomly chosen facial action?</p></div>'
     '<div><h2>Identity</h2><p>The integrating client still needs its trusted identity matcher and final acceptance controls.</p></div></div>'
     '<p class="callout">A camera response or a successful HTTP request is not proof of a live, authenticated person.</p>',
     'Define PAD as checking for a presentation attack such as a photo or screen. Separate liveness from identity matching.'),
    ("One gate in front of capture",
     '<div class="flow"><div>Device<br><small>Webcam or explicit simulator</small></div><b>→</b><div>Quality<br><small>One face, lighting, sharpness</small></div><b>→</b><div>PAD<br><small>Local ONNX inference</small></div><b>→</b><div>Policy<br><small>Passive or active verification</small></div></div>'
     '<div class="branches"><p>Uncertain or required by policy<br><strong>Random action → quality + PAD again</strong></p><p>Attack, engine error, failed action<br><strong>Reject without a captured image</strong></p></div>'
     '<p class="lead">The preview observes the session. Only the capture loop advances its decisions.</p>',
     'Point to the feedback path. The security change is continuous PAD during active verification. The Python service is not a certified SBI.'),
    ("An action cannot override an attack",
     '<ol class="sequence"><li>Issue an unpredictable action from the configured pool.</li><li>Check quality and PAD on subsequent frames.</li><li>Invalidate progress when the face is lost or quality fails.</li><li>Accept only after the workflow criteria are satisfied.</li></ol>'
     '<p class="callout">Errors stop verification. Mock sessions cannot mark actions complete automatically.</p>',
     'Demonstrate the regression test for an attack arriving during an already completed action. State that injected-score tests establish control flow, not image model accuracy.'),
    ("Different policies for different work",
     '<table><thead><tr><th>Workflow</th><th>Passive threshold</th><th>Active actions</th></tr></thead><tbody>'
     '<tr><td>Resident capture</td><td>0.82</td><td>When passive confidence is insufficient</td></tr>'
     '<tr><td>Operator verification</td><td>0.88</td><td>Two required</td></tr>'
     '<tr><td>Supervisor verification</td><td>0.92</td><td>Two required</td></tr></tbody></table>'
     '<p class="lead">Policies run locally. Thresholds and action pools are configurable.</p><p class="caption">These are engineering defaults. They need calibration against deployment data.</p>',
     'Explain that higher thresholds alone are not enough. Required actions cannot be bypassed by a high passive score.'),
    ("A declared model contract",
     '<div class="model-grid"><div class="stat">1.74 MB<small>Packaged MiniFASNet V2 ONNX model</small></div>'
     '<div><h2>Match the upstream input</h2><p>BGR values 0..255. An 80×80 input. A 2.7× face crop. Live class index 1.</p>'
     '<h2>Check the conversion</h2><p>Six deterministic tensors. Maximum absolute logit difference below 0.00000263.</p></div></div>'
     '<p class="caption">Conversion parity only. Attack accuracy, calibration, and cross-device behavior have not been measured here.</p>',
     'Give attribution to Minivision Silent-Face-Anti-Spoofing, Apache 2.0. This is one research model, not the upstream ensemble. A model load is not an accuracy benchmark.'),
    ("Make the result inspectable",
     '<div class="columns"><div><h2>Acceptance tests</h2><p>PAD during actions, face loss, retry limits, engine failures, invalid frames, and concurrent requests.</p></div>'
     '<div><h2>Model updates</h2><p>Signed metadata, Ed25519 verification, persisted downgrade protection, bounded install paths.</p></div>'
     '<div><h2>Operational evidence</h2><p>Model hashes, redacted audit events, anonymous failure/retry rates, and per-process timing.</p></div></div>'
     '<p class="callout">Report unit tests, simulation, model conversion, and physical testing as separate evidence.</p>',
     'Show the current test report. Do not say unit tests prove real attack resistance. Explain the audit chain needs a separate trusted checkpoint.'),
    ("Ready for evaluation, with explicit gaps",
     '<table><thead><tr><th>Available now</th><th>Still required</th></tr></thead><tbody>'
     '<tr><td>Native capture rejection tests</td><td>Live camera and complete active flows</td></tr>'
     '<tr><td>Webcam interface and L0/L1 simulators</td><td>Physical L1 and multiple vendor validation</td></tr>'
     '<tr><td>Tested policy logic and a dataset evaluator</td><td>Consented subjects, real attacks, fixed test thresholds</td></tr>'
     '<tr><td>Android APK and offline model execution</td><td>Measured Android RAM, latency, power, and thermal behavior</td></tr></tbody></table>',
     'Pinned desktop controllers reject synthetic ISO captures. Twelve Android client tests include native inference, the actual signed response parser and one-use onboarding acceptance through a fixture crypto provider. Eight reference camera/debug-launcher tests pass locally. Physical actions, production PKI and complete native camera/UI workflows remain unverified.'),
    ("The next proof belongs in the real client",
     '<p class="lead">On Desktop and Android, show a real attack being rejected before the client accepts a face or completes authentication.</p>'
     '<div class="final-check"><span>Same session</span><span>Same verified image</span><span>No bypass path</span></div>'
     '<p class="strap">Local processing keeps core verification available when the network is unavailable.</p>'
     '<p class="caption">Source, setup, requirement matrix, model card, and evaluation protocol are included in the repository.</p>',
     'Close with the concrete operational value. Provide the repository URL. Use actual evidence rather than predicting a winning probability.'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-css', type=Path, default=ROOT/'pitch/source/viewport-base.css')
    parser.add_argument('--font', type=Path, default=ROOT/'pitch/source/Manrope.ttf')
    args = parser.parse_args()
    font = base64.b64encode(args.font.read_bytes()).decode()
    base_css = args.base_css.read_text(encoding='utf-8')
    css = '''
    @font-face{font-family:Manrope;src:url(data:font/ttf;base64,FONT) format('truetype');font-weight:200 800}
    :root{--stage-bg:#dae3eb;--slide-bg:#f8fbfd;--ink:#16324b;--blue:#124e89;--orange:#ce6812}
    *{box-sizing:border-box}body{font-family:Manrope,sans-serif;color:var(--ink)}
    .slide{padding:105px 120px 110px;border-top:16px solid var(--blue)}
    h1{font-size:88px;line-height:1.12;letter-spacing:-3px;margin:0 0 65px;max-width:1550px;font-weight:800}
    h2{font-size:38px;line-height:1.2;margin:0 0 28px;font-weight:750}
    p,li{font-size:34px;line-height:1.55}.lead{font-size:42px;max-width:1400px;line-height:1.4}
    .strap{font-size:28px;color:var(--blue);margin-top:55px}.caption{font-size:25px;color:#526777;max-width:1500px;line-height:1.45}
    .columns{display:grid;grid-template-columns:1fr 1fr 1fr;gap:65px;margin:50px 0 75px}.columns>div{border-top:5px solid #bdd1df;padding-top:30px}
    .callout{padding:30px 38px;background:#e6eff6;border-left:7px solid var(--blue);font-size:32px}
    .flow{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:65px 0}.flow div{font-size:38px;font-weight:750;border:2px solid #b5c9d8;border-radius:12px;padding:28px;width:350px}.flow small{display:block;font-size:25px;font-weight:400;line-height:1.4;margin-top:14px}.flow b{font-size:40px;color:var(--blue)}
    .branches{display:grid;grid-template-columns:1fr 1fr;gap:65px;border-top:2px solid #bed0dd}.branches p{font-size:29px}.branches strong{display:block;color:var(--blue);margin-top:14px}
    .sequence{padding-left:55px;max-width:1500px}.sequence li{padding-left:20px;margin:30px 0;font-size:38px}
    table{border-collapse:collapse;width:100%;font-size:32px;line-height:1.4;margin:45px 0}th{text-align:left;color:#fff;background:var(--blue);font-weight:650}td,th{padding:28px 32px;border-bottom:2px solid #c9d8e2}tr:nth-child(even){background:#eaf1f6}
    .model-grid{display:grid;grid-template-columns:550px 1fr;gap:110px;align-items:start}.stat{font-size:100px;font-weight:800;letter-spacing:-4px;color:var(--blue);padding-top:40px}.stat small{display:block;font-size:30px;letter-spacing:0;line-height:1.5;font-weight:500}.model-grid p{margin-bottom:42px}
    .face-diagram{position:absolute;right:170px;bottom:160px;width:450px;height:470px;background:#e6eff6;border-radius:20px;display:grid;place-items:center}.face-outline{height:300px;width:220px;border:6px solid var(--blue);border-radius:48% 48% 44% 44%;position:absolute;top:45px}.scan-line{position:absolute;top:196px;left:62px;right:62px;height:6px;background:var(--orange)}.face-diagram span{align-self:end;margin-bottom:42px;font-size:27px;font-weight:700}.slide:first-child h1{max-width:1200px;font-size:108px}.slide:first-child .lead{max-width:1040px}.slide:first-child .strap{margin-top:180px}.final-check{display:flex;gap:28px;margin:75px 0}.final-check span{border-bottom:7px solid var(--orange);padding:28px 30px;font-size:36px;font-weight:700}
    .folio{position:absolute;left:120px;right:120px;bottom:42px;display:flex;justify-content:space-between;font-size:22px;color:#526777}.deck-controls{display:flex;align-items:center;gap:14px;background:white;padding:8px 12px;border-radius:8px;font-size:14px;box-shadow:0 2px 14px #16324b22}button{font:inherit;cursor:pointer;background:white;color:var(--blue);border:1px solid #bed0dd;border-radius:5px;padding:7px 12px}button:focus-visible{outline:3px solid var(--orange)}
    [contenteditable=true]{outline:2px dashed var(--orange)}
    '''.replace('FONT', font)
    sections = []
    for i, (title, body, notes) in enumerate(SLIDES):
        sections.append(f'<section class="slide {"active" if i == 0 else ""}" aria-label="Slide {i+1}: {escape(title)}"><h1>{escape(title)}</h1>{body}<div class="folio"><span>Face liveness / MOSIP Decode 2026</span><span>{i+1:02d} / {len(SLIDES):02d}</span></div><!-- Speaker notes: {escape(notes)} --></section>')
    js = '''
    const slides=[...document.querySelectorAll('.slide')],stage=document.querySelector('.deck-stage');let index=0,editing=false;
    function fit(){const scale=Math.min(innerWidth/1920,innerHeight/1080);stage.style.transform=`translate(${(innerWidth-1920*scale)/2}px,${(innerHeight-1080*scale)/2}px) scale(${scale})`}
    function show(n){index=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.setAttribute('aria-hidden',String(i!==index))});document.querySelector('#count').textContent=(index+1)+' / '+slides.length;location.hash='slide-'+(index+1)}
    document.querySelector('#prev').onclick=()=>show(index-1);document.querySelector('#next').onclick=()=>show(index+1);
    document.querySelector('#edit').onclick=()=>{editing=!editing;document.querySelectorAll('h1,h2,p,td,th,li').forEach(e=>e.contentEditable=String(editing));document.querySelector('#edit').textContent=editing?'Finish editing':'Edit text'};
    document.querySelector('#save').onclick=()=>{const blob=new Blob(['<!doctype html>'+document.documentElement.outerHTML],{type:'text/html'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='face-liveness-pitch.html';a.click();URL.revokeObjectURL(a.href)};
    addEventListener('keydown',e=>{if(editing)return;if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();show(index+1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();show(index-1)}if(e.key==='Home')show(0);if(e.key==='End')show(slides.length-1);if(e.key.toLowerCase()==='e')document.querySelector('#edit').click()});addEventListener('resize',fit);fit();show(Number(location.hash.replace('#slide-',''))-1||0);
    '''
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Face liveness before capture acceptance</title><style>/* === Fixed stage === */'+base_css+'\n/* === Deck design === */'+css+'</style></head><body><div class="deck-viewport"><div class="deck-stage">'+''.join(sections)+'</div></div><nav class="deck-controls" aria-label="Presentation navigation"><button id="prev">Previous</button><span id="count" aria-live="polite"></span><button id="next">Next</button><button id="edit">Edit text</button><button id="save">Save HTML</button></nav><script>'+js+'</script></body></html>'
    output = ROOT/'pitch/index.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(html,encoding='utf-8')
    print(f'Built {len(SLIDES)} slides at {output}')


if __name__=='__main__':
    main()
