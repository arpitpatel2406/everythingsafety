(function () {
        function formatCurrency(amount, locale = 'en-US', currency = 'USD') {
          if (amount == null || isNaN(amount)) return '-'
          try {
            return new Intl.NumberFormat(locale, {
              style: 'currency',
              currency
            }).format(Number(amount))
          } catch {
            return '$' + Number(amount).toFixed(2)
          }
        }

        var PERIOD_TO_DATASET_KEY = {
          day: 'apiDaily',
          week: 'apiWeekly',
          month: 'apiMonthly'
        }

        function getApiUrlFor(period) {
          var key = PERIOD_TO_DATASET_KEY[period]
          return key ? document.body.dataset[key] || null : null
        }

        async function fetchMetrics(period) {
          var url = getApiUrlFor(period)
          if (!url)
            throw new Error('API URL not configured for period: ' + period)
          const resp = await fetch(url, { credentials: 'include' })
          if (!resp.ok)
            throw new Error(
              'Request failed: ' + resp.status + ' ' + resp.statusText
            )
          return resp.json()
        }

        function updateUiFromResponse(data, periodLabel) {
          var totalSalesEl = document.getElementById('totalSales')
          var grossProfitEl = document.getElementById('grossProfit')
          var avgSaleValueEl = document.getElementById('avgSaleValue')
          var salesDeltaEl = document.getElementById('salesDelta')
          var grossProfitDeltaEl = document.getElementById('grossProfitDelta')

          var net = (data && data.totals && data.totals.net) || {}
          var gross = (data && data.totals && data.totals.gross) || {}

          if (totalSalesEl) totalSalesEl.textContent = formatCurrency(net.sales)
          if (grossProfitEl)
            grossProfitEl.textContent = formatCurrency(
              net.profit != null ? net.profit : gross.profit
            )

          var uniqueCount = data && data.filtered_count
          if (avgSaleValueEl) {
            avgSaleValueEl.textContent =
              uniqueCount && Number(uniqueCount) > 0
                ? formatCurrency((net.sales || 0) / Number(uniqueCount))
                : '-'
          }

          if (salesDeltaEl) {
            if (
              data &&
              data.previous &&
              data.previous.totals &&
              data.previous.totals.net
            ) {
              var prev = data.previous.totals.net
              var delta = (net.sales || 0) - (prev.sales || 0)
              salesDeltaEl.textContent =
                "That's " +
                formatCurrency(Math.abs(delta)) +
                ' ' +
                (delta >= 0 ? 'more' : 'less') +
                ' than the previous ' +
                periodLabel +
                '.'
            } else {
              salesDeltaEl.textContent = ''
            }
          }

          if (grossProfitDeltaEl) {
            if (
              data &&
              data.previous &&
              data.previous.totals &&
              data.previous.totals.net
            ) {
              var prevp = data.previous.totals.net
              var pdelta = (net.profit || 0) - (prevp.profit || 0)
              grossProfitDeltaEl.textContent =
                formatCurrency(Math.abs(pdelta)) +
                ' ' +
                (pdelta >= 0 ? 'more' : 'less') +
                ' than the previous ' +
                periodLabel +
                '.'
            } else {
              grossProfitDeltaEl.textContent = ''
            }
          }
        }

        function initPeriodSelector() {
          var container = document.getElementById('periodSelector')
          if (!container) return
          var inputs = container.querySelectorAll('input[name="period"]')
          inputs.forEach(function (input) {
            input.addEventListener('change', function () {
              if (!this.checked) return
              var p = this.dataset.track // 'day' | 'week' | 'month'
              var label =
                { day: 'daily', week: 'weekly', month: 'monthly' }[p] || p

              var totalSalesEl = document.getElementById('totalSales')
              if (totalSalesEl) totalSalesEl.textContent = '…'

              fetchMetrics(p)
                .then(function (data) {
                  updateUiFromResponse(data, label)
                })
                .catch(function (err) {
                  console.error(err)
                  if (totalSalesEl) totalSalesEl.textContent = 'Error'
                  alert('Failed to load ' + label + ' metrics: ' + err.message)
                })
            })
          })

          var checked = container.querySelector('input[name="period"]:checked')
          if (checked) checked.dispatchEvent(new Event('change'))
        }

        document.addEventListener('DOMContentLoaded', initPeriodSelector)
      })()
    