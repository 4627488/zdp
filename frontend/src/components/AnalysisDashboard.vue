<template>
    <v-container fluid>
        <!-- Key Metrics Cards -->
        <v-row>
            <v-col cols="12" md="3">
                <v-card :color="analysis.trend_color" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.trend.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.trend.subtitle', {
                            n: analysis.laplace_factor.toFixed(3)
                            }) }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.trend_assessment }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="primary" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.bestModel.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.bestModel.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.best_model }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="info" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.failures.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.failures.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.total_failures }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="secondary" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.time.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.time.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.total_time.toFixed(2) }}
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Charts Row 1 -->
        <v-row class="mt-4">
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.intensity.title') }}</v-card-title>
                    <v-card-subtitle>{{ $t('analysis.charts.intensity.subtitle') }}</v-card-subtitle>
                    <v-card-text style="height: 300px;">
                        <Line :data="intensityChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.tbf.title') }}</v-card-title>
                    <v-card-subtitle>{{ $t('analysis.charts.tbf.subtitle') }}</v-card-subtitle>
                    <v-card-text style="height: 300px;">
                        <Bar :data="tbfChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Insights Section -->
        <v-row class="mt-4">
            <v-col cols="12">
                <v-card>
                    <v-card-title>{{ $t('analysis.insights.title') }}</v-card-title>
                    <v-card-text>
                        <v-list lines="two">
                            <v-list-item prepend-icon="mdi-information">
                                <v-list-item-title>{{ $t('analysis.insights.trend.title') }}</v-list-item-title>
                                <v-list-item-subtitle>
                                    {{ $t('analysis.insights.trend.desc', {
                                        score: analysis.laplace_factor.toFixed(3),
                                    status: analysis.trend_assessment }) }}
                                </v-list-item-subtitle>
                            </v-list-item>
                            <v-list-item prepend-icon="mdi-trophy">
                                <v-list-item-title>{{ $t('analysis.insights.performance.title') }}</v-list-item-title>
                                <v-list-item-subtitle>
                                    {{ $t('analysis.insights.performance.desc', {
                                        model: analysis.best_model, rmse:
                                    analysis.best_rmse?.toFixed(4) }) }}
                                </v-list-item-subtitle>
                            </v-list-item>
                        </v-list>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js'
import { Line, Bar } from 'vue-chartjs'

const { t } = useI18n()

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
)

const props = defineProps<{
    analysis: any
}>()

const labels = computed(() => Array.from({ length: props.analysis.total_failures }, (_, i) => i + 1))

const intensityChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.intensity.smoothed'),
            data: props.analysis.failure_intensity.smoothed,
            borderColor: '#FF9800',
            backgroundColor: 'rgba(255, 152, 0, 0.2)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
        },
        {
            label: t('analysis.charts.intensity.raw'),
            data: props.analysis.failure_intensity.raw,
            borderColor: '#E0E0E0',
            borderWidth: 1,
            pointRadius: 1,
            fill: false
        }
    ]
}))

const tbfChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.tbf.label'),
            data: props.analysis.tbf_trend,
            backgroundColor: '#2196F3',
            borderRadius: 2
        }
    ]
}))

const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top' as const
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        }
    }
}
</script>
