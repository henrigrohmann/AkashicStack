    def execute(self, cmd_name, args):
        info = self.commands[cmd_name]
        url_path = info['path']
        method = info['method']
        
        # 1. パスパラメータの解決
        # {name} (Set名) の解決を優先
        if "{name}" in url_path:
            if not args:
                console.print("[red]Error: Set name is required.[/red]")
                return
            url_path = url_path.format(name=args[0])
            args = args[1:] # 最初の引数を消費

        # {key} (個別Chunk) の解決
        if "{key}" in url_path:
            val = args[0] if args else self.it
            if not val:
                console.print("[red]Error: Key ($it) is missing.[/red]")
                return
            url_path = url_path.format(key=val)
            args = args[1:] if args else []

        url = f"{self.api_url}{url_path}"
        
        # 2. ペイロードとクエリパラメータの構築
        params = {}
        payload = {}
        
        if method in ["POST", "PUT"]:
            if cmd_name == "write":
                payload = {"content": " ".join(args)}
            elif cmd_name == "tag":
                payload = {"trait": " ".join(args)}
            elif cmd_name == "set_create":
                payload = {"name": args[0] if args else ""}
            elif cmd_name == "set_add":
                # API側の Optional[str] = None に合わせ、クエリまたはパスでkeyを送る
                # $it または 引数があればそれをkeyとして採用
                key_val = args[0] if args else self.it
                params = {"key": key_val}

        try:
            # params(Query) と json(Body) を適切に分離
            resp = httpx.request(method, url, json=payload, params=params)
            
            # ステータスコードに応じた表示
            if resp.is_error:
                console.print(f"[red]Status: {resp.status_code}[/red]")
            
            try:
                data = resp.json()
            except json.JSONDecodeError:
                data = {"text": resp.text}

            # $it の更新ロジック
            # 書き込み、読み込み、またはセット追加成功時に、対象のkeyを保持する
            if isinstance(data, dict):
                # エンジンが返す 'key' 属性を優先的にキャッチ
                new_key = data.get("key")
                if new_key and new_key != "None":
                    self.it = new_key
                    console.print(f"[bold yellow]>> $it updated: {self.it[:8]}...[/bold yellow]")
            
            console.print_json(data=json.dumps(data))
            
        except Exception as e:
            console.print(f"[red]Request Error: {e}[/red]")
