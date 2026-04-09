def display_result(result):
    if isinstance(result, list):
        if not result:
            console.print("[yellow]Empty.[/yellow]")
            return
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("#", style="dim") # シリアル番号
        for key in result[0].keys():
            table.add_column(key)
        
        for idx, item in enumerate(result):
            table.add_row(str(idx), *[str(v) for v in item.values()])
        console.print(table)
    else:
        console.print(result)

def main():
    # --- 1. アダプター初期化 ---
    adapter = AkashaAdapter(mode="stdio")
    
    # --- 2. ウェルカムメッセージ (プロンプトより先に表示) ---
    console.print(Panel("[bold cyan]Akashic Stack CLI[/bold cyan]\n[dim]$it and Serial ID enabled.[/dim]", expand=False))

    # --- 3. ループ開始 ---
    while True:
        try:
            # 入力を受け取る直前に改行を入れるなどして見やすく
            line = input("\nAkasha> ").strip()
            if not line: continue
            # ... (以下、adapter.call と表示ロジック)
