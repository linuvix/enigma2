from enigma import eActionMap
from Tools.KeyBindings import queryKeyBinding, getKeyBindingKeys
from Tools.KeyBindings import ACTION_ALIASES as _KEYBINDING_ALIASES
from Tools.KeyBindings import canonicalAction as _canonicalAction


# --- OpenATV compat ---
#
# Reuse the single, unidirectional alias table from Tools.KeyBindings.
# Resolution is strictly one hop: OpenATV spelling -> OpenPLi canonical
# spelling.  There is NO reverse lookup -- a reverse lookup would turn the
# alias relation into a symmetric set and cause two different spellings to
# resolve to overlapping candidate sets, which poisons keyBindings and
# makes the C++ eActionMap dispatch the wrong action into the wrong
# context.  That collision is what produced the bcm_accel "invalid opcode"
# crash during video playback.
ACTION_ALIASES = _KEYBINDING_ALIASES


def _resolve_action(action, actions):
	"""
	Return the action name to use, given the set of actions the map
	actually registered.

	Priority:
	  1. Exact name (so a plugin that registers both "OK" and "ok" as
	     distinct actions is never shadowed).
	  2. Canonical alias target (OpenATV spelling -> OpenPLi spelling).
	Falls through to the original name if nothing matches.
	"""
	if action in actions:
		return action
	alias = _canonicalAction(action)
	if alias in actions:
		return alias
	return action


def _action_is_bound_anywhere(action):
	"""
	Return True if this action name (or its canonical alias) is bound in
	*any* context by any keymap file loaded so far.

	Used only to suppress spurious "Unknown action" warnings when the map
	itself is registered under a different spelling.  Does not affect
	dispatch -- dispatch uses _resolve_action against self.actions.
	"""
	for candidate in (action, _canonicalAction(action)):
		for context, bound_action in getKeyBindingKeys():
			if bound_action == candidate:
				return True
	return False


class ActionMap:
	def __init__(self, contexts=None, actions=None, prio=0, parentScreen=None):
		self.contexts = contexts or []
		self.actions = actions or {}
		self.prio = prio
		self.p = eActionMap.getInstance()
		self.bound = False
		self.exec_active = False
		self.enabled = True
		# --- OpenATV compat ---
		self.parentScreen = parentScreen.__class__.__name__ if parentScreen else "N/A"
		self.disabledActions = []
		# --- end OpenATV compat ---

		# Undefined-action check is deliberately quiet by default.
		# It is load-order sensitive (a user keymap or plugin keymap can
		# add the binding *after* this ActionMap is constructed) and
		# therefore unreliable outside of a deliberate debugging session.
		# Set E2_DEBUG_UNDEFINED_ACTIONS=1 to re-enable the warning.
		import os
		if os.environ.get("E2_DEBUG_UNDEFINED_ACTIONS") == "1":
			unknown = []
			for action in self.actions:
				matched = False
				for candidate in (action, _canonicalAction(action)):
					for context in self.contexts:
						if queryKeyBinding(context, candidate):
							matched = True
							break
					if matched:
						break
				if not matched and not _action_is_bound_anywhere(action):
					unknown.append(action)
			if unknown:
				print("[ActionMap] Keymap(s) '%s' -> Undefined action(s) '%s'."
					% (", ".join(self.contexts), ", ".join(unknown)))

	def setEnabled(self, enabled):
		self.enabled = enabled
		self.checkBind()

	# --- OpenATV compat ---
	def getEnabled(self):
		return self.enabled

	def setEnabledAction(self, action, enabled):
		resolved = _resolve_action(action, self.actions)
		if resolved in self.actions:
			if enabled and resolved in self.disabledActions:
				self.disabledActions.remove(resolved)
			elif not enabled and resolved not in self.disabledActions:
				self.disabledActions.append(resolved)
	# --- end OpenATV compat ---

	def doBind(self):
		if not self.bound:
			for context in self.contexts:
				self.p.bindAction(context, self.prio, self.action)
			self.bound = True

	def doUnbind(self):
		if self.bound:
			for context in self.contexts:
				self.p.unbindAction(context, self.action)
			self.bound = False

	def checkBind(self):
		if self.exec_active and self.enabled:
			self.doBind()
		else:
			self.doUnbind()

	def execBegin(self):
		self.exec_active = True
		self.checkBind()

	def execEnd(self):
		self.exec_active = False
		self.checkBind()

	def action(self, context, action):
		# --- OpenATV compat: resolve alias and honour disabledActions ---
		resolved = _resolve_action(action, self.actions)
		if resolved in self.actions and resolved not in self.disabledActions:
			if resolved != action:
				print("[ActionMap] Keymap '%s' -> Action = '%s' (alias for '%s')." % (context, resolved, action))
			else:
				print("[ActionMap] Keymap '%s' -> Action = '%s'." % (context, resolved))
			res = self.actions[resolved]()
			if res is not None:
				return res
			return 1
		# If the map itself registered this action name, the only reason
		# we end up here is that the caller is asking for a *different*
		# spelling that couldn't be resolved.  Stay silent -- the alias
		# table has already tried everything it knows.
		if action in self.actions:
			return 0
		# Same: if the action name is globally bound somewhere, silence it.
		# Only warn for names that appear nowhere at all.
		if _action_is_bound_anywhere(action):
			return 0
		print("[ActionMap] Keymap '%s' -> Unknown action '%s'! (Typo in keymap?)" % (context, action))
		return 0
		# --- end OpenATV compat ---

	def destroy(self):
		pass


class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		if action in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") and action in self.actions and action not in self.disabledActions:
			res = self.actions[action](int(action))
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)


class HelpableActionMap(ActionMap):
	# An Actionmap which automatically puts the actions into the helpList.
	#
	# A context list is allowed, and for backward compatibility, a single
	# string context name also is allowed.
	#
	# Sorry for this complicated code.  It's not more than converting a
	# "documented" actionmap (where the values are possibly (function,
	# help)-tuples) into a "classic" actionmap, where values are just
	# functions.  The classic actionmap is then passed to the
	# ActionMapconstructor,	the collected helpstrings (with correct
	# context, action) is added to the screen's "helpList", which will
	# be picked up by the "HelpableScreen".
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		def exists(record):
			for context in parent.helpList:
				if record in context[2]:
					print("[HelpActionMap] removed duplicity: %s %s" % (context[1], record))
					return True
			return False

		if isinstance(contexts, str):
			contexts = [contexts]
		actions = actions or {}
		self.description = description
		adict = {}
		for (action, funchelp) in actions.items():
			adict[action] = funchelp[0] if isinstance(funchelp, tuple) else funchelp

		for context in contexts:
			alist = []
			for (action, funchelp) in actions.items():
				# Resolve the action name so the help list works even when
				# the plugin registered the OpenATV spelling ("keyDown")
				# but the keymap declares the OpenPLi one ("down").
				resolved = _resolve_action(action, adict)
				help_text = funchelp[1] if isinstance(funchelp, tuple) else None
				if queryKeyBinding(context, resolved):
					if not exists((resolved, help_text)):
						alist.append((resolved, help_text))
			parent.helpList.append((self, context, alist))
		ActionMap.__init__(self, contexts, adict, prio, parentScreen=parent)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialise NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialised with
		# these once, via the HelpableActionMap.
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)


# --- OpenATV compat: loadKeymap shim ---
# OpenPLi uses keymapparser instead, so provide a fallback import.
try:
	from keymapparser import readKeymap as loadKeymap
except ImportError:
	def loadKeymap(*args, **kwargs):
		print("[ActionMap] loadKeymap fallback called, but keymapparser is not available")
# --- end OpenATV compat ---


# --- OpenATV compat: re-export KeyBindings functions ---
# OpenATV plugins sometimes import these from Components.ActionMap instead
# of Tools.KeyBindings.  Re-export so those imports succeed.  The functions
# themselves are unchanged; they operate on OpenPLi's Tools.KeyBindings
# global dict, so behaviour is identical to importing them directly.
try:
	from Tools.KeyBindings import (
		addKeyBinding,
		removeKeyBinding,
		removeKeyBindings,
		getKeyBindingKeys,
	)
except ImportError as e:
	print("[ActionMap] WARNING: Could not re-export KeyBindings helpers: %s" % e)
# --- end OpenATV compat ---
