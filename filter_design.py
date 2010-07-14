# -*- coding: utf-8 -*-
from numpy import pi, exp, arange, cos, sin, sqrt, zeros, ones, log, arange
# the three following lines are a workaround for a bug with scipy and py2exe
# together. See http://www.pyinstaller.org/ticket/83 for reference.
from scipy.misc import factorial
import scipy
scipy.factorial = factorial
from scipy.signal import lfilter, cheby1, ellip, butter, iirdesign, freqz, firwin
from scipy.signal.filter_design import ellip, butter, firwin

# bank of filters for any other kind of frequency scale
# http://cobweb.ecn.purdue.edu/~malcolm/apple/tr35/PattersonsEar.pdf
# bandwidth of a cochlear channel as a function of center frequency

# Change the following parameters if you wish to use a different
# ERB scale.
EarQ = 9.26449 # Glasberg and Moore Parameters
minBW = 24.7
order = 1.

NOCTAVE = 8

def frequencies(fs, numChannels, lowFreq):
	channels = arange(0, numChannels)
	cf = -(EarQ*minBW) + exp(channels*(-log(fs/2 + EarQ*minBW) + \
		log(lowFreq + EarQ*minBW))/numChannels) \
		*(fs/2 + EarQ*minBW)
	return cf

def MakeERBFilters(fs, numChannels, lowFreq):
	# [forward, feedback] = MakeERBFilters(fs, numChannels) computes the
	# filter coefficients for a bank of Gammatone filters. These
	# filters were defined by Patterson and Holdworth for simulating
	# the cochlea. The results are returned as arrays of filter
	# coefficients. Each row of the filter arrays (forward and feedback)
	# can be passed to the MatLab "filter" function, or you can do all
	# the filtering at once with the ERBFilterBank() function.
	#
	# The filter bank contains "numChannels" channels that extend from
	# half the sampling rate (fs) to "lowFreq".
	T = 1./fs
	# All of the following expressions are derived in Apple TR #35, "An
	# Efficient Implementation of the Patterson-Holdsworth Cochlear
	# Filter Bank."
	cf = frequencies(fs, numChannels, lowFreq)
	ERB = ((cf/EarQ)**order + minBW**order)**(1./order)
	B = 1.019*2*pi*ERB
	gain = abs((-2*exp(4*1j*cf*pi*T)*T + \
		   2*exp(-(B*T) + 2*1j*cf*pi*T)*T* \
		   (cos(2*cf*pi*T) - sqrt(3. - 2.**(3./2.))* \
		   sin(2*cf*pi*T))) * \
		   (-2*exp(4*1j*cf*pi*T)*T + \
		   2*exp(-(B*T) + 2*1j*cf*pi*T)*T* \
		   (cos(2*cf*pi*T) + sqrt(3. - 2.**(3./2.)) * \
		   sin(2*cf*pi*T)))* \
		   (-2*exp(4*1j*cf*pi*T)*T + \
		   2*exp(-(B*T) + 2*1j*cf*pi*T)*T* \
		   (cos(2*cf*pi*T) - \
		   sqrt(3. + 2.**(3./2.))*sin(2*cf*pi*T))) * \
		   (-2*exp(4*1j*cf*pi*T)*T + 2*exp(-(B*T) + 2*1j*cf*pi*T)*T* \
		   (cos(2*cf*pi*T) + sqrt(3. + 2.**(3./2.))*sin(2*cf*pi*T))) / \
		   (-2 / exp(2*B*T) - 2*exp(4*1j*cf*pi*T) + \
		   2*(1 + exp(4*1j*cf*pi*T))/exp(B*T))**4)
	
	feedback = zeros((len(cf), 9))
	forward = zeros((len(cf), 5))
	forward[:,0] = T**4 / gain
	forward[:,1] = -4*T**4*cos(2*cf*pi*T)/exp(B*T)/gain
	forward[:,2] = 6*T**4*cos(4*cf*pi*T)/exp(2*B*T)/gain
	forward[:,3] = -4*T**4*cos(6*cf*pi*T)/exp(3*B*T)/gain
	forward[:,4] = T**4*cos(8*cf*pi*T)/exp(4*B*T)/gain
	feedback[:,0] = ones(len(cf))
	feedback[:,1] = -8*cos(2*cf*pi*T)/exp(B*T)
	feedback[:,2] = 4*(4 + 3*cos(4*cf*pi*T))/exp(2*B*T)
	feedback[:,3] = -8*(6*cos(2*cf*pi*T) + cos(6*cf*pi*T))/exp(3*B*T)
	feedback[:,4] = 2*(18 + 16*cos(4*cf*pi*T) + cos(8*cf*pi*T))/exp(4*B*T)
	feedback[:,5] = -8*(6*cos(2*cf*pi*T) + cos(6*cf*pi*T))/exp(5*B*T)
	feedback[:,6] = 4*(4 + 3*cos(4*cf*pi*T))/exp(6*B*T)
	feedback[:,7] = -8*cos(2*cf*pi*T)/exp(7*B*T)
	feedback[:,8] = exp(-8*B*T)

	return [forward, feedback]

def ERBFilterBank(forward, feedback, x):
	# y=ERBFilterBank(forward, feedback, x)
	# This function filters the waveform x with the array of filters
	# specified by the forward and feedback parameters. Each row
	# of the forward and feedback parameters are the parameters
	# to the Matlab builtin function "filter".
	(rows, cols) = feedback.shape
	y = zeros((rows, len(x)))
	for i in range(0, rows):
		y[i,:] = lfilter(forward[i,:], feedback[i,:], x)
	return y

# Nominal frequencies: 31.5 40 50 63 80 100 125 160 200 250 315 400 500 630 800 1000 1250
# 1600 2000 Hz, etc.
def octave_frequencies(Nbands, BandsPerOctave):
	f0 = 1000. # audio reference frequency is 1 kHz
	
	b = 1./BandsPerOctave
	
	imax = Nbands/2
	if Nbands%2 == 1:
		i = arange(-imax, imax + 1)
	else:
		i = arange(-imax, imax) + 0.5
	
	fi = f0 * 2**(i*b)
	f_low = fi * sqrt(2**(-b))
	f_high = fi * sqrt(2**b)
	
	return fi, f_low, f_high

def octave_filters(Nbands, BandsPerOctave):
	# Bandpass Filter Generation
	pbrip = .5	# Pass band ripple
	sbrip = 50	# Stop band rejection
	#Filter order
	order = 2

	fi, f_low, f_high = octave_frequencies(Nbands, BandsPerOctave)

	fs = 44100 # sampling rate
	wi = fi/(fs/2.) # normalized frequencies
	w_low = f_low/(fs/2.)
	w_high = f_high/(fs/2.)

	B = []
	A = []
	
	# For each band
	for w, wl, wh in zip(wi, w_low, w_high):
		# normalized frequency vector
		freq = [wl, wh]
	
		# could be another IIR filter
		[b, a] = ellip(order, pbrip, sbrip, freq, btype='bandpass')
		
		B += [b]
		A += [a]
		
	return [B, A, fi, f_low, f_high]

# Note : A way to make the filtering more efficient is to do it with IIR + decimation
# instead of IIR only
# More precisely, we design as much filters as bands per octave (instead of total number
# of bands), and apply it several times on repeatedly decimated signal to go from one octave
# to its lower neighbor
def octave_filters_oneoctave(Nbands, BandsPerOctave):
	# Bandpass Filter Generation
	pbrip = .5	# Pass band ripple
	sbrip = 50	# Stop band rejection
	#Filter order
	order = 2

	fi, f_low, f_high = octave_frequencies(Nbands, BandsPerOctave)

	fi     = fi[-BandsPerOctave:]
	f_low  = f_low[-BandsPerOctave:]
	f_high = f_high[-BandsPerOctave:]

	fs = 44100 # sampling rate
	wi = fi/(fs/2.) # normalized frequencies
	w_low = f_low/(fs/2.)
	w_high = f_high/(fs/2.)

	B = []
	A = []
	
	# For each band
	for w, wl, wh in zip(wi, w_low, w_high):
		# normalized frequency vector
		freq = [wl, wh]
	
		# could be another IIR filter
		[b, a] = ellip(order, pbrip, sbrip, freq, btype='bandpass')
		
		B += [b]
		A += [a]
		
	return [B, A, fi, f_low, f_high]

def octave_filter_bank(forward, feedback, x, zis=None):
	# This function filters the waveform x with the array of filters
	# specified by the forward and feedback parameters. Each row
	# of the forward and feedback parameters are the parameters
	# to the Matlab builtin function "filter".
	Nbank = len(forward)
	y = zeros((Nbank, len(x)))
	
	zfs = []
	y = []
	
	if zis == None:
		zis = []
		for i in range(0, Nbank):
			zis += [zeros(max(len(forward[i]), len(feedback[i]))-1)] 
	
	for i in range(0, Nbank):
		filt, zf = lfilter(forward[i], feedback[i], x, zi=zis[i])
		# zf can be reused to restart the filter
		zfs += [zf]
		y += [filt]
		
	return y, zfs

# Note: we may have one filter in excess here : the low-pass filter for decimation
# does approximately the same thing as the low-pass component of the highest band-pass
# filter for the octave
def octave_filter_bank_decimation(blow, alow, forward, feedback, x, zis=None):
	# This function filters the waveform x with the array of filters
	# specified by the forward and feedback parameters. Each row
	# of the forward and feedback parameters are the parameters
	# to the Matlab builtin function "filter".
	BandsPerOctave = len(forward)
	Nbank = NOCTAVE*BandsPerOctave
	
	y = [0.]*Nbank
	dec = [0.]*Nbank
	
	#b1 = firwin(100, 0.5)
	#x_dec = lfilter(b1, 1., x)
	x_dec = x
	
	zfs = []
	
	if zis == None:
		m = 0
		k = Nbank - 1
	
		for j in range(0, NOCTAVE):
			for i in range(0, BandsPerOctave)[::-1]:
				filt = lfilter(forward[i], feedback[i], x_dec)
				m += 1
				y[k] = filt
				dec[k] = 2**j
				k -= 1
			x_dec = lfilter(blow, alow, x_dec)
			m += 1
			x_dec = x_dec[::2]
		
		return y, dec, None
	else:
		m = 0
		k = Nbank - 1
		
		for j in range(0, NOCTAVE):
			for i in range(0, BandsPerOctave)[::-1]:
				filt, zf = lfilter(forward[i], feedback[i], x_dec, zi=zis[m])
				#filt = lfilter(forward[i], feedback[i], x_dec)
				m += 1
				# zf can be reused to restart the filter
				zfs += [zf]
				#zfs += [0.]
				y[k] = filt
				dec[k] = 2**j
				k -= 1
			x_dec, zf = lfilter(blow, alow, x_dec, zi=zis[m])
			#x_dec = lfilter(blow, alow, x_dec)
			m += 1
			# zf can be reused to restart the filter
			zfs += [zf]
			#zfs += [0.]
			x_dec = x_dec[::2]
		
		return y, dec, zfs

def generate_filters_params():
	import pickle
	
	params = {}
	
	# generate the low-pass filter for decimation
	Ndec = 3
	fc = 0.5
	# other possibilities
	#(bdec, adec) = ellip(Ndec, 0.05, 30, fc)
	#print bdec
	#(bdec, adec) = cheby1(Ndec, 0.05, fc)
	#(bdec, adec) = butter(Ndec, fc)
	(bdec, adec) = iirdesign(0.48, 0.50, 0.05, 70, analog=0, ftype='ellip', output='ba')
	#bdec = firwin(30, fc)
	#adec = [1.]
	
	params['dec'] = [bdec, adec]
	
	#generate the octave filters
	for BandsPerOctave in [1,3,6,12,24]:
		Nbands = NOCTAVE*BandsPerOctave
		[boct, aoct, fi, flow, fhigh] = octave_filters_oneoctave(Nbands, BandsPerOctave)
		params['%d' %BandsPerOctave] = [boct, aoct, fi, flow, fhigh]
	
	output = open('generated_filters.pkl', 'wb')
	# Pickle dictionary using protocol 0.
	pickle.dump(params, output)
	# Pickle the list using the highest protocol available.
	#pickle.dump(selfref_list, output, -1)
	output.close()

def load_filters_params():
	import pickle
		
	input = open('generated_filters.pkl', 'rb')
	# Pickle dictionary using protocol 0.
	params = pickle.load(input)
	# Pickle the list using the highest protocol available.
	#pickle.load(input, -1)
	input.close()
	
	return params

# main() is a test function
def main():
	from matplotlib.pyplot import semilogx, plot, show, xlim, ylim, figure, legend, subplot, bar
	from numpy.fft import fft, fftfreq, fftshift, ifft
	from numpy import log10, linspace, interp, angle, array, concatenate

	N = 2048*2*2
	fs = 44100.
	Nchannels = 20
	low_freq = 20.

	impulse = zeros(N)
	impulse[N/2] = 1
	f = 1000.
	#impulse = sin(2*pi*f*arange(0, N/fs, 1./fs))

	#[ERBforward, ERBfeedback] = MakeERBFilters(fs, Nchannels, low_freq)
	#y = ERBFilterBank(ERBforward, ERBfeedback, impulse)

	BandsPerOctave = 1
	Nbands = NOCTAVE*BandsPerOctave
	
	[B, A, fi, fl, fh] = octave_filters(Nbands, BandsPerOctave)
	y, zfs = octave_filter_bank(B, A, impulse)
	
	response = 20.*log10(abs(fft(y)))
	freqScale = fftfreq(N, 1./fs)
	
	figure()
	subplot(211)
	
	for i in range(0, response.shape[0]):
		semilogx(freqScale[0:N/2],response[i, 0:N/2])
		
	xlim(fs/2000, fs)
	ylim(-70, 10)
	
	subplot(212)
	m = 0
	for f in fi:
		p = 10.*log10((y[m]**2).mean())
		m += 1
		semilogx(f, p, 'ko')
	
	Ndec = 3
	fc = 0.5
	# other possibilities
	#(bdec, adec) = ellip(Ndec, 0.05, 30, fc)
	#print bdec
	#(bdec, adec) = cheby1(Ndec, 0.05, fc)
	#(bdec, adec) = butter(Ndec, fc)
	(bdec, adec) = iirdesign(0.48, 0.50, 0.05, 70, analog=0, ftype='ellip', output='ba')
	#bdec = firwin(30, fc)
	#adec = [1.]
	
	figure()
	subplot(211)
	
	response = 20.*log10(abs(fft(impulse)))
	plot(fftshift(freqScale), fftshift(response), label="impulse")
	
	y = lfilter(bdec, adec, impulse)
	response = 20.*log10(abs(fft(y)))
	plot(fftshift(freqScale), fftshift(response), label="lowpass")
	
	ydec = y[::2].repeat(2)
	response = 20.*log10(abs(fft(ydec)))
	plot(fftshift(freqScale), fftshift(response), label="lowpass + dec2 + repeat2")
	
	ydec2 = interp(range(0, len(y)), range(0, len(y), 2), y[::2])
	response = 20.*log10(abs(fft(ydec2)))
	plot(fftshift(freqScale), fftshift(response), label="lowpass + dec2 + interp2")
	
	ydec3 = y[::2]
	response = 20.*log10(abs(fft(ydec3)))
	freqScale2 = fftfreq(N/2, 2./fs)
	plot(freqScale2,fftshift(response), label="lowpass + dec2")
	
	legend(loc="lower left")
	
	subplot(212)
	plot(range(0, len(impulse)), impulse, label="impulse")
	plot(range(0, len(impulse)), y, label="lowpass")
	plot(range(0, len(impulse)), ydec, label="lowpass + dec2 + repeat2")
	plot(range(0, len(impulse)), ydec2, label="lowpass + dec2 + interp2")
	plot(range(0, len(impulse), 2), ydec3, label="lowpass + dec2")
	legend()
	
	[boct, aoct, fi, flow, fhigh] = octave_filters_oneoctave(Nbands, BandsPerOctave)
	y, dec, zfs = octave_filter_bank_decimation(bdec, adec, boct, aoct, impulse)

	figure()
	subplot(211)
	
	for yone, d in zip(y, dec):
		response = 20.*log10(abs(fft(yone))*d)
		freqScale = fftfreq(N/d, 1./(fs/d))
		semilogx(freqScale[0:N/(2*d)],response[0:N/(2*d)])
	
	xlim(fs/2000, fs)
	ylim(-70, 10)
	
	subplot(212)
	m = 0
	for i in range(0, NOCTAVE):
		for f in fi:
			p = 10.*log10((y[m]**2).mean())
			semilogx(f/dec[m], p, 'ko')
			m += 1

	[boct, aoct, fi, flow, fhigh] = octave_filters_oneoctave(Nbands, BandsPerOctave)
	y1, dec, zfs = octave_filter_bank_decimation(bdec, adec, boct, aoct, impulse[0:N/2])
	y2, dec, zfs = octave_filter_bank_decimation(bdec, adec, boct, aoct, impulse[N/2:], zis=zfs)	
	
	y = []
	for y1one, y2one in zip(y1,y2):
		y += [concatenate((y1one,y2one))]

	figure()
	subplot(211)
	
	for yone, d in zip(y, dec):
		response = 20.*log10(abs(fft(yone))*d)
		freqScale = fftfreq(N/d, 1./(fs/d))
		semilogx(freqScale[0:N/(2*d)],response[0:N/(2*d)])
	
	xlim(fs/2000, fs)
	ylim(-70, 10)
	
	subplot(212)
	m = 0
	for i in range(0, NOCTAVE):
		for f in fi:
			p = 10.*log10((y[m]**2).mean())
			semilogx(f/dec[m], p, 'ko')
			m += 1
	
	generate_filters_params()

	show()
	
if __name__ == "__main__":
	main()