"""Tests for models.py - Mention model."""



class TestMentionModel:
    """Tests for the Mention model."""

    def test_mention_model_exists(self):
        """Test that Mention model can be imported."""
        from models import Mention
        assert Mention is not None

    def test_mention_creation(self):
        """Test creating a Mention instance."""
        from models import Mention

        mention = Mention(tweet_id="12345")
        assert mention.tweet_id == "12345"
        assert mention.processed is False  # Default value

    def test_mention_default_values(self):
        """Test Mention default values."""
        from models import Mention

        mention = Mention(tweet_id="123")
        assert mention.processed is False
        assert mention.tweet_text is None
        assert mention.twitter_username is None
        assert mention.build_id is None

    def test_mention_with_all_fields(self):
        """Test Mention with all fields."""
        from models import Mention

        mention = Mention(
            tweet_id="12345",
            tweet_text="Test tweet",
            twitter_username="testuser",
            processed=True,
            build_id="build-uuid",
        )

        assert mention.tweet_id == "12345"
        assert mention.tweet_text == "Test tweet"
        assert mention.twitter_username == "testuser"
        assert mention.processed is True
        assert mention.build_id == "build-uuid"

    def test_mention_id_is_string(self):
        """Test that Mention ID is a string (UUID)."""
        from models import Mention

        mention = Mention(tweet_id="123")
        # ID should be set automatically as a UUID string
        assert mention.id is not None
        assert isinstance(mention.id, str)

    def test_mention_processed_flag(self):
        """Test Mention processed flag."""
        from models import Mention

        mention1 = Mention(tweet_id="1", processed=False)
        mention2 = Mention(tweet_id="2", processed=True)

        assert mention1.processed is False
        assert mention2.processed is True
