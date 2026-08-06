"""Versioned D-Bus interface definitions shipped with the prototype."""

ACTION_BROKER_XML = """<node>
  <interface name="org.voiceos.ActionBroker1">
    <method name="Submit">
      <arg name="request_json" type="s" direction="in"/>
      <arg name="result_json" type="s" direction="out"/>
    </method>
    <method name="GetCapabilities">
      <arg name="capabilities_json" type="s" direction="out"/>
    </method>
  </interface>
</node>"""

TRUSTED_CONFIRM_XML = """<node>
  <interface name="org.voiceos.TrustedConfirm1">
    <method name="Begin">
      <arg name="request_json" type="s" direction="in"/>
      <arg name="confirmation_json" type="s" direction="out"/>
    </method>
    <method name="Approve">
      <arg name="confirmation_id" type="s" direction="in"/>
      <arg name="phrase" type="s" direction="in"/>
      <arg name="pin_fd" type="h" direction="in"/>
      <arg name="capability" type="s" direction="out"/>
    </method>
    <method name="Deny">
      <arg name="confirmation_id" type="s" direction="in"/>
    </method>
  </interface>
</node>"""

