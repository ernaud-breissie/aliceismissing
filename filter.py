def callback(commit, metadata):
    # Replace bussiere's author information if present
    if commit.author_name == b"bussiere" or commit.author_email == b"bussiere@gmail.com":
        commit.author_name = b"anonymous"
        commit.author_email = b"anonymous@example.com"
    
    # Replace bussiere's committer information if present
    if commit.committer_name == b"bussiere" or commit.committer_email == b"bussiere@gmail.com":
        commit.committer_name = b"anonymous"
        commit.committer_email = b"anonymous@example.com"
    
    return True

