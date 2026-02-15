from dataclasses import dataclass, field

class ValidationError(ValueError):
    pass

@dataclass
class First100Set:
    start: int = 1
    end: int = 100
    extracted: set[int] = field(default_factory=set)
    remaining: set[int] = field(init=False)

    def __post_init__(self) -> None:
        self.remaining = set(range(self.start, self.end + 1))

    def extract(self, n: int) -> None:
        """
        Extraer un elemento
        valida que sea entero y rasngo correcto, y que no haya sido extraido antes
        """
        if not isinstance(n, int):
            raise ValidationError("El número debe ser un entero.")
        if n < self.start or n > self.end:
            raise ValidationError(f"El número debe estar entre {self.start} y {self.end}.")
        if n in self.extracted:
            raise ValidationError("Ese número ya fue extraído.")
        # Simula la extraccion
        self.remaining.remove(n)
        self.extracted.add(n)

    def missing(self) -> int:
        """
        regresa el numero faltante
        """
        if len(self.extracted) != 1:
            raise ValidationError("Debe extraerse exactamente 1 número para poder calcular el faltante.")
        # Queda un conjunto con 99 elementos, el faltante es el unico extraido
        return next(iter(self.extracted))

    def missing_by_sum(self) -> int:
        """
        calcular los valores faltantes con sumas
        """
        if len(self.extracted) != 1:
            raise ValidationError("Debe extraerse exactamente 1 número para poder calcular el faltante.")
        expected_sum = (self.end * (self.end + 1)) // 2  # 1 - 100
        current_sum = sum(self.remaining)
        return expected_sum - current_sum
