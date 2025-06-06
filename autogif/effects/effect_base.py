from abc import ABC, abstractmethod

class EffectBase(ABC):
    """
    Base class for all subtitle effects.
    Each effect plugin must inherit from this class.
    """

    @property
    @abstractmethod
    def slug(self) -> str:
        """A unique, kebab-case identifier for the effect (e.g., 'shake', 'neon-glow')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """A user-friendly name for the effect displayed in the UI (e.g., 'Shake', 'Neon Glow')."""
        pass

    @property
    @abstractmethod
    def default_intensity(self) -> int:
        """The default intensity for the effect (0-100)."""
        pass

    @property
    @abstractmethod
    def supports_word_level(self) -> bool:
        """Whether this effect can be applied to individual words rather than entire captions."""
        pass

    @abstractmethod
    def prepare(self, **kwargs) -> None:
        """
        Called once per render before processing any frames.
        Allows the effect to initialize or precompute any necessary data.
        kwargs can include things like total_frames, fps, text_duration, etc.
        """
        pass

    @abstractmethod
    def transform(self, frame_image, text: str, base_position: tuple[int, int], current_frame_index: int, intensity: int, **kwargs):
        """
        Transforms a single frame.
        Args:
            frame_image: The RGBA frame (e.g., a Pillow Image object or NumPy array) to be modified.
            text: The current subtitle text to be rendered.
            base_position: A tuple (x, y) representing the calculated base position for the text.
            current_frame_index: The index of the current frame being processed.
            intensity: The user-defined intensity for this effect (0-100).
            kwargs: Additional context if needed by specific effects.
        Returns:
            The modified RGBA frame_image.
        """
        pass 