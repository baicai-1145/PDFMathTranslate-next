<template>
  <div class="app-container">
    <router-view />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--surface-primary);
  transition: background 0.35s ease, color 0.35s ease;
}
</style>
