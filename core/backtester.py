"""
Backtesting Module
Test trading strategies on historical data to optimize performance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class Backtester:
    """Backtest trading strategies on historical data"""

    def __init__(self):
        """Initialize backtester"""
        self.results = {}

    def run_backtest(
        self,
        df: pd.DataFrame,
        strategy_config: Dict,
        initial_balance: float = 1000
    ) -> Dict:
        """
        Run backtest on historical data

        Args:
            df: Historical price data
            strategy_config: Strategy parameters
            initial_balance: Starting balance

        Returns:
            Dictionary with backtest results
        """
        if len(df) < 100:
            return {'error': 'Not enough data for backtesting'}

        balance = initial_balance
        position = None
        trades = []
        equity_curve = [initial_balance]

        # Strategy parameters
        rsi_oversold = strategy_config.get('rsi_oversold', 30)
        rsi_overbought = strategy_config.get('rsi_overbought', 70)
        min_confidence = strategy_config.get('min_confidence', 60)

        # Calculate indicators
        from core.indicators import TechnicalIndicators

        df['rsi'] = TechnicalIndicators.rsi(df['close'], 14)
        macd = TechnicalIndicators.macd(df['close'])
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['signal']
        df['ema_short'] = TechnicalIndicators.ema(df['close'], 9)
        df['ema_long'] = TechnicalIndicators.ema(df['close'], 21)
        df['volume_ma'] = df['volume'].rolling(20).mean()

        # Simulate trading
        for i in range(50, len(df)):
            current_data = df.iloc[i]
            price = current_data['close']

            # Generate signal
            signal = self._generate_signal(current_data, strategy_config)

            # Execute trades
            if position is None and signal in ['BUY', 'STRONG_BUY']:
                # Enter long
                position = {
                    'entry_price': price,
                    'entry_time': df.index[i],
                    'size': balance * 0.95,  # Use 95% of balance
                    'type': 'LONG'
                }
                balance = balance * 0.05  # Keep 5% as reserve

            elif position and position['type'] == 'LONG':
                # Check exit conditions
                exit_signal = False
                exit_reason = ""

                if signal in ['SELL', 'STRONG_SELL']:
                    exit_signal = True
                    exit_reason = "Signal reversal"
                elif current_data['rsi'] > rsi_overbought:
                    exit_signal = True
                    exit_reason = "RSI overbought"
                elif self._calculate_stop_loss(position, price, 0.02):
                    exit_signal = True
                    exit_reason = "Stop loss (2%)"

                if exit_signal:
                    # Close position
                    pnl = (price - position['entry_price']) / position['entry_price']
                    pnl_amount = position['size'] * pnl
                    balance = position['size'] + pnl_amount

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': price,
                        'pnl_pct': round(pnl * 100, 2),
                        'pnl_amount': round(pnl_amount, 2),
                        'reason': exit_reason
                    })

                    position = None

            # Track equity
            if position:
                unrealized_pnl = (price - position['entry_price']) / position['entry_price']
                current_equity = balance + position['size'] * (1 + unrealized_pnl)
            else:
                current_equity = balance

            equity_curve.append(current_equity)

        # Calculate metrics
        if trades:
            win_rate = len([t for t in trades if t['pnl_pct'] > 0]) / len(trades) * 100
            avg_win = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]) if any(t['pnl_pct'] > 0 for t in trades) else 0
            avg_loss = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]) if any(t['pnl_pct'] < 0 for t in trades) else 0
            total_return = (balance - initial_balance) / initial_balance * 100
            max_drawdown = self._calculate_max_drawdown(equity_curve)
            sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            total_return = 0
            max_drawdown = 0
            sharpe_ratio = 0

        return {
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'total_return': round(total_return, 2),
            'final_balance': round(balance, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            'trades': trades[-10:]  # Last 10 trades
        }

    def _generate_signal(self, data: pd.Series, config: Dict) -> str:
        """Generate trading signal from indicators"""
        signals = []

        # RSI
        if data['rsi'] < config.get('rsi_oversold', 30):
            signals.append('BUY')
        elif data['rsi'] > config.get('rsi_overbought', 70):
            signals.append('SELL')

        # MACD
        if data['macd'] > data['macd_signal']:
            signals.append('BUY')
        else:
            signals.append('SELL')

        # EMA
        if data['ema_short'] > data['ema_long']:
            signals.append('BUY')
        else:
            signals.append('SELL')

        # Volume
        if data['volume'] > data['volume_ma'] * 1.5:
            # Volume spike - reinforce signal
            pass

        # Count signals
        buy_signals = signals.count('BUY')
        sell_signals = signals.count('SELL')

        if buy_signals >= 2:
            return 'STRONG_BUY'
        elif buy_signals == 1:
            return 'BUY'
        elif sell_signals >= 2:
            return 'STRONG_SELL'
        elif sell_signals == 1:
            return 'SELL'
        else:
            return 'HOLD'

    def _calculate_stop_loss(self, position: Dict, current_price: float, stop_pct: float) -> bool:
        """Check if stop loss is hit"""
        if position['type'] == 'LONG':
            loss_pct = (position['entry_price'] - current_price) / position['entry_price']
            return loss_pct >= stop_pct
        return False

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        peak = equity_curve[0]
        max_dd = 0

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(self, equity_curve: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if len(equity_curve) < 2:
            return 0

        returns = pd.Series(equity_curve).pct_change().dropna()

        if returns.std() == 0:
            return 0

        sharpe = returns.mean() / returns.std() * np.sqrt(252)  # Annualized
        return sharpe

    def optimize_parameters(
        self,
        df: pd.DataFrame,
        param_ranges: Dict
    ) -> Dict:
        """
        Optimize strategy parameters using grid search

        Args:
            df: Historical data
            param_ranges: Ranges for parameters to test

        Returns:
            Best parameters and results
        """
        best_return = -999
        best_params = None
        best_results = None

        # Generate parameter combinations
        rsi_values = param_ranges.get('rsi_oversold', [25, 30, 35])
        confidence_values = param_ranges.get('min_confidence', [55, 60, 65, 70])

        total_tests = len(rsi_values) * len(confidence_values)
        current_test = 0

        print(f"Running {total_tests} optimization tests...")

        for rsi_os in rsi_values:
            for conf in confidence_values:
                current_test += 1

                config = {
                    'rsi_oversold': rsi_os,
                    'rsi_overbought': 100 - rsi_os,
                    'min_confidence': conf
                }

                results = self.run_backtest(df, config)

                if results.get('total_return', 0) > best_return:
                    best_return = results['total_return']
                    best_params = config
                    best_results = results

                print(f"Test {current_test}/{total_tests}: Return={results.get('total_return', 0):.1f}%")

        return {
            'best_parameters': best_params,
            'best_results': best_results,
            'tests_run': total_tests
        }

    def compare_strategies(
        self,
        df: pd.DataFrame,
        strategies: List[Dict]
    ) -> Dict:
        """
        Compare multiple strategies side by side

        Args:
            df: Historical data
            strategies: List of strategy configurations

        Returns:
            Comparison results
        """
        comparison = {}

        for i, strategy in enumerate(strategies):
            name = strategy.get('name', f'Strategy_{i+1}')
            results = self.run_backtest(df, strategy)
            comparison[name] = results

        return comparison
