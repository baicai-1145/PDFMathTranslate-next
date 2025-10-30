<template>
  <div class="app-container">
    <router-view />
    <auth-dialog />
  </div>
</template>

<script setup lang="ts">
import AuthDialog from '@/components/auth/AuthDialog.vue';
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--surface-primary);
  transition: background 0.35s ease, color 0.35s ease;
}
</style>
