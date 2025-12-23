<template>
    <Bar :data="chartData" :options="chartOptions" />
</template>

<script setup lang="ts">
import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    BarElement,
    CategoryScale,
    LinearScale
} from 'chart.js'
import { Bar } from 'vue-chartjs'
import { computed } from 'vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
    originalDistribution: { labels: number[], counts: number[] } | null
    processedDistribution: { labels: number[], counts: number[] } | null
}>()

const chartData = computed(() => {
    // Use labels from original if available, or processed
    const labels = props.originalDistribution?.labels.map(l => l.toFixed(2)) ||
        props.processedDistribution?.labels.map(l => l.toFixed(2)) || []

    const datasets = []

    if (props.originalDistribution) {
        datasets.push({
            label: 'Original Distribution',
            backgroundColor: 'rgba(158, 158, 158, 0.5)',
            data: props.originalDistribution.counts
        })
    }

    if (props.processedDistribution) {
        datasets.push({
            label: 'Processed Distribution',
            backgroundColor: 'rgba(25, 118, 210, 0.5)',
            data: props.processedDistribution.counts
        })
    }

    return {
        labels,
        datasets
    }
})

const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top' as const
        },
        title: {
            display: true,
            text: 'Data Distribution'
        }
    }
}
</script>
