
@app.route('/admin/delete/<int:post_id>', methods=['GET'])
@login_required # New admin role check is here
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # CRITICAL LOGIC FLAW STILL EXISTS
    if current_user.role != 'ADMIN':
        app.logger.critical(f"Admin {current_user.username} (role: {current_user.role}) attempted to delete post {post_id}.")
        abort(403)
    
    db.session.delete(post)
    db.session.commit()

    # This log line is the "smoking gun" our Log-Watcher will find
    app.logger.critical(f"ADMIN ACTION: User {current_user.username} (role: {current_user.role}) deleted post {post_id}.")
    return f"Post {post_id} deleted by {current_user.username}."
