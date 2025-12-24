FROM oven/bun:1

WORKDIR /app

# Copy dependency definitions
COPY package.json bun.lock ./

# Install dependencies
RUN bun install

# Copy source
COPY . .

# Check if SvelteKit needs a sync (creates .svelte-kit)
RUN bun run prepare

# Expose port 5173 (Vite default)
EXPOSE 5173

# Start development server with host binding
CMD ["bun", "run", "dev", "--", "--host"]
