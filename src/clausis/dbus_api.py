"""Versioned D-Bus interface definitions shipped with the prototype."""

ACTION_BROKER_XML = """<node>
  <interface name="org.clausis.ActionBroker1">
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
  <interface name="org.clausis.TrustedConfirm1">
    <method name="ConfirmAndSubmit">
      <arg name="request_json" type="s" direction="in"/>
      <arg name="result_json" type="s" direction="out"/>
    </method>
  </interface>
</node>"""
