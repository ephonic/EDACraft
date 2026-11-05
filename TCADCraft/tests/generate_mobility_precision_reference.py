"""Independent 100-decimal reference for the declared mobility parameter set."""
from decimal import Decimal, localcontext
from pathlib import Path
import argparse


def reference_text():
    D = Decimal
    points = [('273.15', '1.234567890123e22', '5.678901234567e21'),
              ('333.333333333333333333', '9.876543210987e23', '1.234567890123e22'),
              ('450.125', '3.141592653589793238462643383279e25',
               '2.718281828459045235360287e24')]
    lines = ['# model electron temperature_K donor_m-3 acceptor_m-3 mobility_m2_Vs\n',
             '# Decimal precision100; repository formula, not measured/commercial data\n']
    with localcontext() as context:
        context.prec = 100
        for model in (1, 2):
            for electron in (1, 0):
                for temp, donor, acceptor in points:
                    T, Nd, Na = map(D, (temp, donor, acceptor))
                    if model == 1:
                        lo, hi, ref, alpha, beta = map(D, ('52.2', '1417', '9.68e16', '.68', '-.66')
                            if electron else ('49.9', '470.5', '2.23e17', '.72', '-2.05'))
                        mobility = (lo+(hi-lo)/(1+((Nd+Na)*D('1e-6')/ref)**alpha)*(T/300)**beta)*D('1e-4')
                    else:
                        phonon = D(1400 if electron else 450)*(T/300)**D('-1.5')
                        impurity = D('1e17')*T**D('1.5')/((Nd if electron else Na)*D('1e-6'))
                        mobility = 1/(1/phonon+1/impurity)*D('1e-4')
                    lines.append(f'{model} {electron} {temp} {donor} {acceptor} {mobility:.60E}\n')
    return ''.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).resolve().parent/'data/mobility_precision.tsv'
    text = reference_text()
    if args.check:
        assert target.read_text() == text
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as stream:
            stream.write(text)
    print('12 independent Decimal reference cases verified' if args.check else '12 reference cases written')
