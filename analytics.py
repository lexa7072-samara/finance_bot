from typing import List, Dict
from collections import defaultdict

class Analytics:
    @staticmethod
    def calculate_totals(expenses: List[Dict]) -> Dict:
        totals = defaultdict(float)
        
        for expense in expenses:
            totals[expense['category']] += expense['amount']
        
        total_sum = sum(totals.values())
        
        return {
            'by_category': dict(totals),
            'total': total_sum,
            'count': len(expenses)
        }
    
    @staticmethod
    def calculate_income_totals(income: List[Dict]) -> Dict:
        totals = defaultdict(float)
        
        for item in income:
            totals[item['category']] += item['amount']
        
        total_sum = sum(totals.values())
        
        return {
            'by_category': dict(totals),
            'total': total_sum,
            'count': len(income)
        }
    
    @staticmethod
    def format_report(totals: Dict, month_name: str, income_total: float = 0, previous_balance: float = 0) -> str:
        if totals['count'] == 0 and income_total == 0 and previous_balance == 0:
            return "📊 Отчёт за " + month_name + "\n\nРасходов не найдено."
        
        report = "📊 Отчёт за " + month_name + "\n\n"
        
        # Показываем остаток с прошлого месяца
        if previous_balance != 0:
            if previous_balance > 0:
                report += "💰 Остаток с прошлого месяца: +" + str(round(previous_balance, 2)) + " руб.\n"
            else:
                report += "⚠️ Долг с прошлого месяца: " + str(round(previous_balance, 2)) + " руб.\n"
        
        # Доход за текущий месяц
        if income_total > 0:
            report += "💵 Доход за месяц: " + str(round(income_total, 2)) + " руб.\n"
        
        # Общий бюджет (остаток + доход)
        total_budget = previous_balance + income_total
        if total_budget > 0 and (previous_balance != 0 or income_total > 0):
            report += "📈 Общий бюджет: " + str(round(total_budget, 2)) + " руб.\n"
        
        report += "\n"
        
        if totals['count'] > 0:
            report += "📉 Расходы:\n"
            
            sorted_categories = sorted(
                totals['by_category'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for category, amount in sorted_categories:
                if total_budget > 0:
                    percentage = (amount / total_budget) * 100
                    report += "• " + category + ": " + str(round(amount, 2)) + " руб. (" + str(round(percentage, 1)) + "%)\n"
                else:
                    report += "• " + category + ": " + str(round(amount, 2)) + " руб.\n"
            
            report += "\n💰 Итого расходов: " + str(round(totals['total'], 2)) + " руб."
            
            if total_budget > 0:
                spent_percent = (totals['total'] / total_budget) * 100
                report += " (" + str(round(spent_percent, 1)) + "%)"
        
        # Итоговый остаток
        final_balance = total_budget - totals['total']
        report += "\n\n"
        if final_balance >= 0:
            report += "✅ Остаток: " + str(round(final_balance, 2)) + " руб."
        else:
            report += "❌ Перерасход: " + str(round(abs(final_balance), 2)) + " руб."
        
        report += "\n📝 Записей: " + str(totals['count'])
        
        return report
    
    @staticmethod
    def format_income_report(totals: Dict, month_name: str) -> str:
        if totals['count'] == 0:
            return "💵 Доходы за " + month_name + "\n\nДоходов не найдено."
        
        report = "💵 Доходы за " + month_name + "\n\n"
        
        sorted_categories = sorted(
            totals['by_category'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for category, amount in sorted_categories:
            percentage = (amount / totals['total']) * 100
            report += "• " + category + ": " + str(round(amount, 2)) + " руб. (" + str(round(percentage, 1)) + "%)\n"
        
        report += "\n💰 Итого: " + str(round(totals['total'], 2)) + " руб."
        report += "\n📝 Записей: " + str(totals['count'])
        
        return report