"""
Result Tracker - Track all predictions and outcomes for backtesting
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class BetResult:
    """Represents a single bet result"""
    timestamp: str
    symbol: str
    market_type: str  # 'binary' or 'interval'
    market_id: str
    market_question: str
    signal: str  # 'YES', 'NO', 'LOW', 'MID', 'HIGH'
    confidence: float
    predicted_price: Optional[float]
    target_price: Optional[float]  # For binary: the price threshold
    current_price: float
    time_until_resolved: int  # minutes
    outcome: str  # What we bet on
    actual_result: Optional[str]  # 'YES' or 'NO' (for binary), 'LOW', 'MID', 'HIGH' (for interval)
    is_win: Optional[bool]  # True = won, False = lost, None = pending
    amount_bet: float
    amount_won: Optional[float]  # Positive = won, Negative = lost
    edge: Optional[float]  # Our probability - implied probability from odds
    prediction_time: Optional[str] = None  # When prediction was made (XX:45)
    expected_resolve_time: Optional[str] = None  # When market resolves (XX:00)


class ResultTracker:
    """Track all predictions and calculate performance metrics"""

    def __init__(self, db_path: str = "results.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market_type TEXT NOT NULL,
                market_id TEXT,
                market_question TEXT,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                predicted_price REAL,
                target_price REAL,
                current_price REAL NOT NULL,
                time_until_resolved INTEGER,
                outcome TEXT NOT NULL,
                actual_result TEXT,
                is_win BOOLEAN,
                amount_bet REAL DEFAULT 0,
                amount_won REAL,
                edge REAL,
                raw_data TEXT,
                prediction_time TEXT,
                expected_resolve_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add new columns if table exists (for existing databases)
        try:
            cursor.execute("ALTER TABLE bets ADD COLUMN prediction_time TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE bets ADD COLUMN expected_resolve_time TEXT")
        except:
            pass

        # Market snapshots (for backtesting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                snapshot_time TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT NOT NULL,
                yes_price REAL,
                no_price REAL,
                yes_volume REAL,
                no_volume REAL,
                low_price REAL,
                mid_price REAL,
                high_price REAL,
                close_time TEXT,
                resolve_time TEXT,
                UNIQUE(market_id, snapshot_time)
            )
        """)

        # Performance metrics cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_bets INTEGER DEFAULT 0,
                winning_bets INTEGER DEFAULT 0,
                losing_bets INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                total_bet_amount REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                roi REAL DEFAULT 0,
                avg_edge REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def log_bet(self, bet: BetResult, raw_analysis: Dict = None):
        """
        Log a new bet to database

        Args:
            bet: BetResult dataclass
            raw_analysis: Full signal analysis dict (for debugging)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bets (
                timestamp, symbol, market_type, market_id, market_question,
                signal, confidence, predicted_price, target_price, current_price,
                time_until_resolved, outcome, actual_result, is_win,
                amount_bet, amount_won, edge, raw_data, prediction_time, expected_resolve_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bet.timestamp, bet.symbol, bet.market_type, bet.market_id, bet.market_question,
            bet.signal, bet.confidence, bet.predicted_price, bet.target_price, bet.current_price,
            bet.time_until_resolved, bet.outcome, bet.actual_result, bet.is_win,
            bet.amount_bet, bet.amount_won, bet.edge,
            json.dumps(raw_analysis) if raw_analysis else None,
            bet.prediction_time, bet.expected_resolve_time
        ))

        conn.commit()
        conn.close()

    def update_bet_result(self, market_id: str, actual_result: str, is_win: bool, amount_won: float = 0):
        """
        Update a bet with actual result after market resolves

        Args:
            market_id: Unhedged market ID
            actual_result: 'YES', 'NO', 'LOW', 'MID', 'HIGH'
            is_win: Whether we won or lost
            amount_won: Amount won (positive) or lost (negative)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE bets
            SET actual_result = ?, is_win = ?, amount_won = ?
            WHERE market_id = ? AND actual_result IS NULL
        """, (actual_result, is_win, amount_won, market_id))

        conn.commit()
        conn.close()

    def get_stats(self, days: int = 7, symbol: str = None) -> Dict:
        """
        Get performance statistics

        Args:
            days: Number of days to look back
            symbol: Filter by symbol (optional)

        Returns:
            Dict with stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        where_clause = "WHERE actual_result IS NOT NULL"
        params = []

        if symbol:
            where_clause += " AND symbol = ?"
            params.append(symbol)

        if days > 0:
            where_clause += " AND date(timestamp) >= date('now', '-{} days')".format(days)

        # Total bets
        cursor.execute(f"SELECT COUNT(*) FROM bets {where_clause}", params)
        total_bets = cursor.fetchone()[0]

        if total_bets == 0:
            return {
                'total_bets': 0,
                'win_rate': 0,
                'profit_loss': 0,
                'roi': 0
            }

        # Winning bets
        cursor.execute(f"SELECT COUNT(*) FROM bets {where_clause} AND is_win = 1", params)
        winning_bets = cursor.fetchone()[0]

        # Total bet amount
        cursor.execute(f"SELECT SUM(amount_bet) FROM bets {where_clause}", params)
        total_bet = cursor.fetchone()[0] or 0

        # Total won
        cursor.execute(f"SELECT SUM(amount_won) FROM bets {where_clause}", params)
        total_won = cursor.fetchone()[0] or 0

        # Win rate
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0

        # Profit/Loss
        profit_loss = total_won - total_bet

        # ROI
        roi = (profit_loss / total_bet * 100) if total_bet > 0 else 0

        # Avg edge
        cursor.execute(f"SELECT AVG(edge) FROM bets {where_clause} AND edge IS NOT NULL", params)
        avg_edge = cursor.fetchone()[0] or 0

        # By symbol breakdown
        cursor.execute(f"""
            SELECT symbol, COUNT(*) as bets, SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                   SUM(amount_won) - SUM(amount_bet) as pnl
            FROM bets {where_clause}
            GROUP BY symbol
            ORDER BY pnl DESC
        """, params)
        by_symbol = cursor.fetchall()

        conn.close()

        return {
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'losing_bets': total_bets - winning_bets,
            'win_rate': round(win_rate, 2),
            'total_bet_amount': round(total_bet, 2),
            'total_won': round(total_won, 2),
            'profit_loss': round(profit_loss, 2),
            'roi': round(roi, 2),
            'avg_edge': round(avg_edge, 2),
            'by_symbol': [{'symbol': row[0], 'bets': row[1], 'wins': row[2], 'pnl': round(row[3], 2)} for row in by_symbol]
        }

    def get_pending_bets(self) -> List[Dict]:
        """Get all pending bets (not yet resolved)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM bets WHERE actual_result IS NULL
            ORDER BY timestamp DESC
        """)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def get_recent_bets(self, limit: int = 50) -> List[Dict]:
        """Get recent bets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM bets
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def print_stats(self, days: int = 7):
        """Print pretty stats table"""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        stats = self.get_stats(days=days)

        console.print(f"\n[bold cyan]Performance Stats (Last {days} days)[/bold cyan]\n")

        # Main stats
        console.print(f"  Total Bets: [bold]{stats['total_bets']}[/bold]")
        console.print(f"  Win Rate: [bold{' green' if stats['win_rate'] >= 60 else ' red'}] {stats['win_rate']}%[/bold{' green' if stats['win_rate'] >= 60 else ' red'}]")
        console.print(f"  Profit/Loss: [bold{' green' if stats['profit_loss'] >= 0 else ' red'}] ${stats['profit_loss']:.2f}[/bold{' green' if stats['profit_loss'] >= 0 else ' red'}]")
        console.print(f"  ROI: [bold{' green' if stats['roi'] >= 0 else ' red'}] {stats['roi']:.2f}%[/bold{' green' if stats['roi'] >= 0 else ' red'}]")

        if stats.get('avg_edge', 0) > 0:
            console.print(f"  Avg Edge: [cyan]{stats['avg_edge']:.2f}%[/cyan]")

        # By symbol
        if stats.get('by_symbol'):
            console.print(f"\n[bold]By Symbol:[/bold]")
            table = Table()
            table.add_column("Symbol", style="cyan")
            table.add_column("Bets", justify="right")
            table.add_column("Wins", justify="right")
            table.add_column("Win Rate", justify="right")
            table.add_column("P/L", justify="right")

            for s in stats['by_symbol']:
                win_rate = (s['wins'] / s['bets'] * 100) if s['bets'] > 0 else 0
                pnl_style = "green" if s['pnl'] >= 0 else "red"
                table.add_row(
                    s['symbol'],
                    str(s['bets']),
                    str(s['wins']),
                    f"{win_rate:.1f}%",
                    f"[{pnl_style}]${s['pnl']:.2f}[/{pnl_style}]"
                )

            console.print(table)

    def get_hourly_benchmark(self, hours: int = 24) -> Dict:
        """
        Get hourly benchmark summary (predictions vs results)

        Args:
            hours: Number of hours to look back

        Returns:
            Dict with hourly breakdown
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get predictions from last N hours
        cursor.execute("""
            SELECT
                strftime('%Y-%m-%d %H:00', timestamp) as hour,
                symbol,
                signal,
                confidence,
                COUNT(*) as predictions,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN is_win IS NULL THEN 1 ELSE 0 END) as pending
            FROM bets
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' hours')
            GROUP BY hour, symbol
            ORDER BY hour DESC, symbol
        """, (hours,))

        rows = cursor.fetchall()
        conn.close()

        # Format results
        benchmark = {}
        for row in rows:
            hour, symbol, signal, conf, preds, wins, losses, pending = row

            if hour not in benchmark:
                benchmark[hour] = {
                    'hour': hour,
                    'symbols': {},
                    'total_predictions': preds,
                    'total_wins': wins,
                    'total_losses': losses,
                    'total_pending': pending,
                    'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                }

            benchmark[hour]['symbols'][symbol] = {
                'signal': signal,
                'confidence': conf,
                'predictions': preds,
                'wins': wins,
                'losses': losses,
                'pending': pending,
                'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else None
            }

        return benchmark

    def get_latest_benchmark(self) -> Dict:
        """
        Get latest benchmark summary (last prediction batch)

        Returns:
            Dict with latest predictions and results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get latest predictions (from most recent XX:45)
        cursor.execute("""
            SELECT
                prediction_time,
                symbol,
                signal,
                confidence,
                market_question,
                current_price,
                predicted_price,
                actual_result,
                is_win
            FROM bets
            WHERE prediction_time IS NOT NULL
            ORDER BY prediction_time DESC, symbol
            LIMIT 20
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {'predictions': [], 'summary': {}}

        # Group by prediction time
        by_time = {}
        for row in rows:
            pred_time, symbol, signal, conf, question, curr_price, pred_price, actual, is_win = row

            if pred_time not in by_time:
                by_time[pred_time] = {
                    'predictions': [],
                    'resolved': 0,
                    'wins': 0,
                    'losses': 0,
                    'pending': 0
                }

            by_time[pred_time]['predictions'].append({
                'symbol': symbol,
                'signal': signal,
                'confidence': conf,
                'question': question,
                'current_price': curr_price,
                'predicted_price': pred_price,
                'actual_result': actual,
                'is_win': is_win,
                'status': 'resolved' if is_win is not None else 'pending'
            })

            if is_win is not None:
                by_time[pred_time]['resolved'] += 1
                if is_win:
                    by_time[pred_time]['wins'] += 1
                else:
                    by_time[pred_time]['losses'] += 1
            else:
                by_time[pred_time]['pending'] += 1

        # Return most recent
        latest_time = sorted(by_time.keys(), reverse=True)[0] if by_time else None

        if latest_time:
            latest = by_time[latest_time]
            win_rate = (latest['wins'] / latest['resolved'] * 100) if latest['resolved'] > 0 else 0

            return {
                'prediction_time': latest_time,
                'predictions': latest['predictions'],
                'resolved': latest['resolved'],
                'wins': latest['wins'],
                'losses': latest['losses'],
                'pending': latest['pending'],
                'win_rate': win_rate
            }

        return {'predictions': [], 'summary': {}}

    def print_benchmark(self, hours: int = 24):
        """Print benchmark summary"""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print(f"\n[bold cyan]Hourly Benchmark (Last {hours} hours)[/bold cyan]\n")

        benchmark = self.get_hourly_benchmark(hours=hours)

        if not benchmark:
            console.print("[yellow]No benchmark data yet[/yellow]")
            return

        for hour, data in sorted(benchmark.items(), reverse=True):
            console.print(f"[bold]{hour}[/bold]")
            console.print(f"  Predictions: {data['total_predictions']} | "
                         f"Wins: [green]{data['total_wins']}[/green] | "
                         f"Losses: [red]{data['total_losses']}[/red] | "
                         f"Pending: {data['total_pending']}")
            console.print(f"  Win Rate: {data['win_rate']:.1f}%\n")

            # Show by symbol
            for symbol, stats in data['symbols'].items():
                console.print(f"    [cyan]{symbol}[/cyan]: {stats['signal']} @ {stats['confidence']:.0f}% | "
                             f"[green]{stats['wins']}W[/green] [red]{stats['losses']}L[/red] ({stats['pending']} pending)")

        # Latest summary
        console.print("\n[bold]Latest Predictions:[/bold]")
        latest = self.get_latest_benchmark()
        if latest.get('prediction_time'):
            console.print(f"  Time: {latest['prediction_time']}")
            console.print(f"  Resolved: {latest['resolved']}/{latest['resolved'] + latest['pending']}")
            console.print(f"  Win Rate: {latest['win_rate']:.1f}%")

            for pred in latest['predictions'][:8]:
                status_color = "green" if pred['status'] == 'resolved' and pred['is_win'] else \
                               "red" if pred['status'] == 'resolved' and not pred['is_win'] else "yellow"
                console.print(f"    [{status_color}]{pred['symbol']}[/ {status_color}]: "
                             f"{pred['signal']} ({pred['status']})")


def test_tracker():
    """Test the result tracker"""
    from rich.console import Console

    console = Console()

    console.print("[cyan]Testing Result Tracker...[/cyan]\n")

    tracker = ResultTracker()

    # Log a test bet
    bet = BetResult(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        symbol='BTCUSDT',
        market_type='binary',
        market_id='test_market_123',
        market_question='BTC above $67000 at 12:00 PM?',
        signal='YES',
        confidence=85.0,
        predicted_price=67500.0,
        target_price=67000.0,
        current_price=67200.0,
        time_until_resolved=25,
        outcome='YES',
        actual_result=None,
        is_win=None,
        amount_bet=10.0,
        amount_won=None,
        edge=5.0  # Our 85% vs implied odds
    )

    tracker.log_bet(bet)

    console.print("[green]OK[/green] Test bet logged")

    # Get stats
    stats = tracker.get_stats(days=1)
    console.print(f"\n[cyan]Stats:[/cyan]")
    console.print(f"  Total bets: {stats['total_bets']}")
    console.print(f"  Pending: {stats['total_bets']}")

    # Print pretty
    tracker.print_stats(days=1)

    console.print("\n[green]OK[/green] Result tracker working!")


if __name__ == "__main__":
    test_tracker()
