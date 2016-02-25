import inspect
from keras.models import *
from theano import function

def clone_model(model, input_shape, clone_weights=False):
  if type(nn) is Graph: raise Exception('only Sequential nets are supported')
  return build_sequential([clone_layer(l, clone_weights) for l in model.layers], input_shape)

def clone_layer(layer, clone_weights=False):
  args, _, _, defaults = inspect.getargspec(layer.__init__)  
  mandatories = len(args) if defaults is None else len(args) - len(defaults)
  ctor_args = {}
  for i, arg in enumerate(args):
    if arg == 'self' or not hasattr(layer, arg): continue        
    val = getattr(layer, arg)
    if arg == 'layers': val = [clone_layer(l, clone_weights) for l in val]    
    if inspect.isfunction(val): val = val.__name__

    default_idx = i - mandatories
    if default_idx < 0 or defaults[default_idx] != val: ctor_args[arg] = val
  cloned = type(layer)(**ctor_args)
  if clone_weights: cloned.set_weights(layer.get_weights())
  return cloned

def _get_activations_impl(model, target_layer_index, X_batch):
    return function(
      [model.layers[0].input], model.layers[target_layer_index].get_output(train=False), 
      allow_input_downcast=True)(X_batch)

def get_activations(nn, X, y, target_layer_name,
  epochs=3, batch_size=128, folds=5,
  loss='binary_crossentropy', optimizer='rmsprop'):
  if type(nn) is Graph: raise Exception('only Sequential nets are supported')

  if not type(X) is dict and hasattr(X, 'values'): X = X.values
  if not type(y) is dict and hasattr(y, 'values'): y = y.values
  np.random.seed(0)

  target_layer_index = (i for i, l in enumerate(nn.layers) 
      if target_layer_name == l.name).next()

  def op(X1, y1, X2):
    nn2 = clone_model(nn, X.shape)
    nn2.compile(loss=loss, optimizer=optimizer)
    nn2.fit(X1, y1, nb_epoch=epochs, batch_size=batch_size)  
    return _get_activations_impl(nn, target_layer_index, X2)

  return self_chunked_op(X, y, op, cv=folds)
  