import numpy as np
from bayespy.nodes import GaussianARD, Gamma
from bayespy.inference import VB
import bayespy.plot as bpplt

data = np.random.normal(5, 10, size=(10,))


mu = GaussianARD(0, 1e-6)
tau = Gamma(1e-6, 1e-6)
y = GaussianARD(mu, tau, plates=(10,))

y.observe(data)
print(y)

Q = VB(mu, tau, y)
Q.update(repeat=20)


bpplt.pyplot.subplot(2, 1, 1)
bpplt.pdf(mu, np.linspace(-10, 20, num=100), color='k', name=r'\mu')
bpplt.pyplot.subplot(2, 1, 2)
bpplt.pdf(tau, np.linspace(1e-6, 0.08, num=100), color='k', name=r'\tau')
bpplt.pyplot.tight_layout()
bpplt.pyplot.show()