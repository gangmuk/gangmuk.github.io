serve:
	ruby scripts/prepare_posts.rb
	bundle exec jekyll serve --livereload

build:
	ruby scripts/prepare_posts.rb
	bundle exec jekyll build

dev:
	ruby scripts/prepare_posts.rb
	bundle exec jekyll serve --livereload &
	@echo "Watching _posts/*/post.md for changes (Ctrl+C to stop)..."
	@touch .watch_sentinel; \
	while true; do \
		sleep 1; \
		if find _posts -name "post.md" -newer .watch_sentinel | grep -q .; then \
			ruby scripts/prepare_posts.rb; \
			touch .watch_sentinel; \
		fi; \
	done
