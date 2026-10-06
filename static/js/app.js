// Set today's date and load initial summary
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }

    const currentDateDisplay = document.getElementById('currentDateDisplay');
    if (currentDateDisplay) {
        const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
        currentDateDisplay.textContent = new Date().toLocaleDateString('en-US', options);
    }

    // Load initial data
    loadSummary();
    setInterval(loadSummary, 10000); // Refresh every 10 seconds
});

// Add Expense Submit Handler
async function handleExpenseSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();

    const amountInput = document.getElementById('amount');
    const descriptionInput = document.getElementById('description');
    const dateInput = document.getElementById('date');

    if (!amountInput || !descriptionInput) return false;

    const amount = parseFloat(amountInput.value);
    const description = descriptionInput.value.trim();
    const date = dateInput && dateInput.value ? dateInput.value : new Date().toISOString().split('T')[0];

    if (isNaN(amount) || amount <= 0 || !description) {
        alert('⚠️ Please enter a valid expense amount and description.');
        return false;
    }

    const expense = { amount, description, date };

    try {
        const response = await fetch('/add_expense', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(expense)
        });

        const data = await response.json().catch(() => ({}));

        if (response.status === 401) {
            window.location.href = data.redirect || '/login';
            return false;
        }

        if (response.ok && data.success) {
            amountInput.value = '';
            descriptionInput.value = '';
            if (dateInput) dateInput.valueAsDate = new Date();
            await loadSummary();
        } else {
            alert('❌ Error adding expense: ' + (data.error || 'Failed to save expense.'));
        }
    } catch (err) {
        console.error("Error adding expense", err);
        alert("❌ Network error adding expense. Please try again.");
    }
    return false;
}

// Budget Submit Handler
async function handleBudgetSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    await updateBudget();
    return false;
}

// Update Budget
async function updateBudget() {
    const budgetInput = document.getElementById('budgetInput') || document.getElementById('budget');
    if (!budgetInput) {
        alert("Budget input field not found.");
        return;
    }
    const budget = parseFloat(budgetInput.value);
    
    if (isNaN(budget) || budget <= 0) {
        alert("Please enter a valid monthly budget limit greater than 0.");
        return;
    }

    try {
        const response = await fetch('/update_budget', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget })
        });

        const data = await response.json().catch(() => ({}));

        if (response.status === 401) {
            window.location.href = data.redirect || '/login';
            return;
        }

        if (response.ok && data.success) {
            budgetInput.value = '';
            await loadSummary();
        } else {
            alert('❌ Error updating budget: ' + (data.error || 'Failed to update budget.'));
        }
    } catch (err) {
        console.error("Error updating budget", err);
        alert("❌ Network error updating budget. Please try again.");
    }
}

// Delete Expense
async function deleteExpense(expenseId) {
    if (!confirm("Are you sure you want to delete this expense entry?")) return;

    try {
        const response = await fetch(`/delete_expense/${expenseId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json().catch(() => ({}));

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (response.ok && data.success) {
            await loadSummary();
        } else {
            alert('❌ Error: ' + (data.error || 'Failed to delete expense.'));
        }
    } catch (err) {
        console.error("Error deleting expense", err);
    }
}

const categoryColors = {
    'food': 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-300 dark:border-amber-700',
    'transport': 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-300 dark:border-blue-700',
    'shopping': 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200 border border-rose-300 dark:border-rose-700',
    'entertainment': 'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200 border border-purple-300 dark:border-purple-700',
    'utilities': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200 border border-indigo-300 dark:border-indigo-700',
    'health': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700',
    'education': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/60 dark:text-yellow-200 border border-yellow-300 dark:border-yellow-700',
    'others': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600'
};

const insightColors = {
    'warning': 'bg-red-50 text-red-700 border-l-4 border-red-500 dark:bg-red-900/30 dark:text-red-300',
    'caution': 'bg-amber-50 text-amber-700 border-l-4 border-amber-500 dark:bg-amber-900/30 dark:text-amber-300',
    'success': 'bg-emerald-50 text-emerald-700 border-l-4 border-emerald-500 dark:bg-emerald-900/30 dark:text-emerald-300',
    'info': 'bg-blue-50 text-blue-700 border-l-4 border-blue-500 dark:bg-blue-900/30 dark:text-blue-300',
    'tip': 'bg-indigo-50 text-indigo-700 border-l-4 border-indigo-500 dark:bg-indigo-900/30 dark:text-indigo-300'
};

// Load Summary
async function loadSummary() {
    try {
        const response = await fetch('/get_summary');
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await response.json();

        // Update metric display cards
        const budgetDisplay = document.getElementById('budgetDisplay');
        const spentDisplay = document.getElementById('spentDisplay');
        const remainingDisplay = document.getElementById('remainingDisplay');
        const savingsRateDisplay = document.getElementById('savingsRateDisplay');

        const budgetVal = Number(data.summary.budget || 0);
        const spentVal = Number(data.summary.total_spent || 0);
        const remainingVal = Number(data.summary.remaining || 0);

        if (budgetDisplay) budgetDisplay.textContent = `₹${budgetVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (spentDisplay) spentDisplay.textContent = `₹${spentVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (remainingDisplay) {
            remainingDisplay.textContent = `₹${remainingVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            if (remainingVal < 0) {
                remainingDisplay.className = "text-2xl font-extrabold text-red-600 dark:text-red-400";
            } else {
                remainingDisplay.className = "text-2xl font-extrabold text-emerald-600 dark:text-emerald-400";
            }
        }

        if (savingsRateDisplay) {
            if (budgetVal > 0) {
                const rate = ((remainingVal / budgetVal) * 100).toFixed(1);
                savingsRateDisplay.textContent = `${Math.max(0, rate)}%`;
            } else {
                savingsRateDisplay.textContent = `0.0%`;
            }
        }

        // Update insights
        const insightsContainer = document.getElementById('insightsContainer');
        if (insightsContainer) {
            if (data.insights && data.insights.length > 0) {
                const insightsHtml = data.insights.map(insight =>
                    `<div class="p-3 rounded-xl shadow-sm text-xs font-medium ${insightColors[insight.type] || insightColors['info']}">${insight.message}</div>`
                ).join('');
                insightsContainer.innerHTML = insightsHtml;
            } else {
                insightsContainer.innerHTML = '<p class="text-center text-gray-400 dark:text-gray-500 py-6 text-sm">Add expenses to receive real-time AI insights!</p>';
            }
        }

        // Update expense count badge
        const expenseCountBadge = document.getElementById('expenseCountBadge');
        if (expenseCountBadge) {
            expenseCountBadge.textContent = `${data.expenses ? data.expenses.length : 0} items`;
        }

        // Update expenses list (Display newest first)
        const expensesList = document.getElementById('expensesList');
        if (expensesList) {
            if (data.expenses && data.expenses.length > 0) {
                const expensesHtml = data.expenses.map(expense => `
                    <div class="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl flex justify-between items-center border border-gray-100 dark:border-gray-700/80 hover:shadow-sm transition">
                        <div class="flex-1 pr-2">
                            <div class="font-semibold text-gray-800 dark:text-gray-200 text-xs sm:text-sm">${escapeHtml(expense.description)}</div>
                            <div class="flex items-center gap-2 mt-1">
                                <span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${categoryColors[expense.category] || categoryColors['others']}">${expense.category}</span>
                                <span class="text-[11px] text-gray-500 dark:text-gray-400">📅 ${expense.date}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-2.5">
                            <div class="text-sm sm:text-base font-bold text-indigo-600 dark:text-indigo-400">₹${Number(expense.amount).toFixed(2)}</div>
                            <button onclick="deleteExpense(${expense.id})" title="Delete Expense" aria-label="Delete Expense ${escapeHtml(expense.description)}" class="text-gray-400 hover:text-red-500 p-1 text-sm transition rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40">
                                🗑️
                            </button>
                        </div>
                    </div>
                `).join('');
                expensesList.innerHTML = expensesHtml;
            } else {
                expensesList.innerHTML = '<p class="text-center text-gray-400 dark:text-gray-500 py-6 text-sm">No expenses added yet.</p>';
            }
        }

        // Update category chart
        const categoryChart = document.getElementById('categoryChart');
        if (categoryChart) {
            if (data.summary.by_category && Object.keys(data.summary.by_category).length > 0) {
                const chartHtml = Object.entries(data.summary.by_category)
                    .sort((a, b) => b[1] - a[1])
                    .map(([category, amount]) => {
                        const percentage = spentVal > 0 ? (amount / spentVal) * 100 : 0;
                        return `
                            <div>
                                <div class="flex justify-between text-xs mb-1">
                                    <span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${categoryColors[category] || categoryColors['others']}">${category}</span>
                                    <span class="font-semibold dark:text-gray-200">₹${Number(amount).toFixed(2)} (${percentage.toFixed(1)}%)</span>
                                </div>
                                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
                                    <div class="bg-gradient-to-r from-indigo-500 to-purple-600 h-2 rounded-full transition-all duration-500" style="width: ${Math.min(100, Math.max(2, percentage))}%"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                categoryChart.innerHTML = chartHtml;
            } else {
                categoryChart.innerHTML = '<p class="text-center text-gray-400 dark:text-gray-500 py-6 text-sm">No expenses categorized yet.</p>';
            }
        }
    } catch (err) {
        console.error("Error loading summary", err);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Chat functionality
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML += `<div class="mb-3 p-3 rounded-xl max-w-[85%] bg-gradient-to-br from-indigo-600 to-purple-600 text-white ml-auto shadow-sm text-xs">${escapeHtml(message)}</div>`;
        input.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json().catch(() => ({ response: "Sorry, I encountered an issue processing your question." }));
            const botText = data.response ? data.response.replace(/\n/g, '<br>') : "Sorry, no response available.";
            
            chatMessages.innerHTML += `<div class="mb-3 p-3 rounded-xl max-w-[85%] bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 shadow-sm border border-gray-200 dark:border-gray-600 text-xs">${botText}</div>`;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (err) {
            console.error("Error sending message", err);
        }
    }
}
